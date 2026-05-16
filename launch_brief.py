"""
launch_brief.py — end-to-end orchestrator for the Utopia Launch Brief agent.

One command runs the full pipeline: fetch transcript → generate brief →
route to Slack + Linear.

Usage:
    python launch_brief.py --latest        # use most recent Granola meeting
    python launch_brief.py --pick          # pick from a numbered list
    python launch_brief.py --list          # just list recent Granola meetings
    python launch_brief.py not_xxxxx       # specific Granola note ID
    python launch_brief.py samples/x.txt   # local transcript file
    python launch_brief.py --latest --no-route   # generate brief, skip routing
"""

import argparse
import sys

from primary_agent import (
    fetch_transcript,
    attach_runtime_meta,
    generate_brief_from_transcript,
    save_brief
)
from handoff_agent import main as run_handoff, post_to_slack
from granola_client import GranolaClient


def list_recent_granola_notes(limit: int = 10):
    """Fetch and return recent Granola notes for picking or listing."""
    client = GranolaClient()
    notes = client.list_notes().get("notes", [])
    if not notes:
        raise RuntimeError("No notes found in your Granola account.")
    return notes[:limit]


def print_note_list(notes):
    print("\nRecent Granola meetings:\n", file=sys.stderr)
    for i, note in enumerate(notes, 1):
        title = (note.get("title") or "Untitled")[:60]
        date = (note.get("created_at") or "?")[:10]
        print(f"  [{i}] {date}  {note['id']}  {title}", file=sys.stderr)


def pick_note_interactively(notes):
    print_note_list(notes)
    while True:
        choice = input(f"\nPick a number (1-{len(notes)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(notes):
                return notes[idx]["id"]
        except ValueError:
            pass
        print("Invalid choice. Try again.", file=sys.stderr)

def build_list_blocks(notes: list, limit: int = 5) -> list:
    """Slack Block Kit for the recent-meetings list with copyable run commands."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 Recent Granola meetings"},
        },
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": "Copy a command below and run it locally to process that meeting.",
            }],
        },
        {"type": "divider"},
    ]
    for note in notes[:limit]:
        title = (note.get("title") or "Untitled")[:80]
        date = (note.get("created_at") or "?")[:10]
        nid = note["id"]
        text = f"*{date}* · {title}\n```\npython launch_brief.py {nid}\n```"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})
    return blocks


def post_granola_list_to_slack(limit: int = 5) -> int:
    """Fetch recent Granola notes and post them to Slack with copyable run commands."""
    try:
        notes = list_recent_granola_notes(limit=limit)
    except Exception as e:
        print(f"✗ Failed to fetch Granola notes: {e}", file=sys.stderr)
        return 2

    if not notes:
        print("No notes found in your Granola account.", file=sys.stderr)
        return 1

    print(f"→ Posting {len(notes)} recent meetings to Slack...", file=sys.stderr)
    try:
        blocks = build_list_blocks(notes, limit=limit)
        ts = post_to_slack(blocks, f"{len(notes)} recent Granola meetings")
        print(f"  ✓ List posted (ts={ts})", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"✗ Slack post failed: {e}", file=sys.stderr)
        return 2

def resolve_source(args) -> str | None:
    """Figure out what transcript source to use based on CLI args."""
    if args.list:
        print_note_list(list_recent_granola_notes())
        return None  # exit early after listing
    if args.latest:
        latest = list_recent_granola_notes(limit=1)[0]
        print(f"→ Using latest Granola note: {latest['id']}", file=sys.stderr)
        print(f"  Title: {latest.get('title', 'Untitled')}", file=sys.stderr)
        return latest["id"]
    if args.pick:
        return pick_note_interactively(list_recent_granola_notes())
    if args.source:
        return args.source
    return None


def generate_brief(source: str) -> str:
    """Stage 1 + 2: fetch transcript and produce the brief."""
    print(f"→ Generating brief from {source}", file=sys.stderr)
    transcript = fetch_transcript(source)
    brief = generate_brief_from_transcript(transcript["transcript_text"])
    brief = attach_runtime_meta(brief, transcript["id"])
    brief_path = save_brief(brief)
    print(f"  ✓ Brief saved: {brief_path}", file=sys.stderr)
    return str(brief_path)

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Utopia Launch Brief — end-to-end agent (transcript → drafts in Slack + Linear).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Granola note ID (not_xxx) or path to local transcript file",
    )
    parser.add_argument("--latest", action="store_true", help="Use the most recent Granola note")
    parser.add_argument(
    "--post-list",
    action="store_true",
    help="Post recent Granola meetings to Slack with copyable run commands",
)
    parser.add_argument("--pick", action="store_true", help="Interactive picker from recent Granola notes")
    parser.add_argument("--list", action="store_true", help="List recent Granola notes and exit")
    parser.add_argument("--no-route", action="store_true", help="Generate brief only; skip Slack/Linear routing")
    args = parser.parse_args()
    
    if args.post_list:
      return post_granola_list_to_slack()

    source = resolve_source(args)
    if source is None:
        if args.list:
            return 0
        parser.print_help()
        return 1

    # Stage 1: generate the brief
    brief_path = generate_brief(source)

    if args.no_route:
        print(brief_path)  # for piping
        return 0

    # Stage 2: route via handoff agent
    print("→ Stage 2: routing to Slack and Linear", file=sys.stderr)
    sys.argv = ["handoff_agent.py", brief_path]
    return run_handoff()


if __name__ == "__main__":
    sys.exit(main())