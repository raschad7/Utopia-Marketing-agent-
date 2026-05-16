"""
handoff_agent.py — Utopia Launch Brief router (unified Slack workflow)

Consumes a JSON brief from primary_agent.py. Posts ONE rich Slack message
containing all three drafts (LinkedIn + email + press angle) plus a review
checklist. Also creates a Linear issue for the press angle as a trackable
task, linked from the Slack message.

If meeting_assessment.is_publishable is false, posts a "skipped" notice
and stops — no drafts, no Linear issue.

Usage:
    python handoff_agent.py outputs/brief_20260515_193828.json
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from slack_sdk import WebClient # type: ignore
from slack_sdk.errors import SlackApiError # type: ignore

load_dotenv()

LINEAR_API_URL = "https://api.linear.app/graphql"


def create_linear_issue(press_angle: dict, meta: dict) -> tuple[str, str]:
    """Create a Linear issue for the press angle. Returns (url, identifier)."""
    api_key = os.environ.get("LINEAR_API_KEY")
    team_id = os.environ.get("LINEAR_TEAM_ID")
    if not api_key or not team_id:
        raise ValueError("LINEAR_API_KEY and LINEAR_TEAM_ID must be set.")

    bullets = "\n".join(f"- {pt}" for pt in press_angle.get("supporting_points", []))
    description = (
        f"**Target publication:** {press_angle.get('target_publication_type', 'TBD')}\n\n"
        f"**Supporting points:**\n{bullets}\n\n"
        f"**Why newsworthy:** {press_angle.get('reasoning', '')}\n\n"
        f"---\n"
        f"_Source meeting: {meta.get('meeting_title', 'Untitled')} "
        f"({meta.get('meeting_date', 'unknown')})_"
    )

    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier url }
      }
    }
    """
    payload = {
        "query": mutation,
        "variables": {
            "input": {
                "teamId": team_id,
                "title": press_angle["headline"],
                "description": description,
            }
        },
    }
    r = requests.post(
        LINEAR_API_URL,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json=payload,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(f"Linear errors: {data['errors']}")
    if not data["data"]["issueCreate"]["success"]:
        raise RuntimeError("Linear issueCreate returned success=false")
    issue = data["data"]["issueCreate"]["issue"]
    return issue["url"], issue["identifier"]


def build_skip_blocks(meta: dict, assessment: dict) -> list:
    """Slack blocks for a 'no publishable content' notice."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "⊘ Meeting skipped — no content drafted"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Meeting:*\n{meta.get('meeting_title', 'Untitled')}"},
                {"type": "mrkdwn", "text": f"*Date:*\n{meta.get('meeting_date', 'unknown')}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Reason:* {assessment.get('reasoning', 'No reason given')}",
            },
        },
    ]


def build_brief_blocks(
    brief: dict,
    linear_url: str | None,
    linear_id: str | None,
    linear_error: str | None = None,
) -> list:
    """Slack blocks for a full unified content brief."""
    meta = brief.get("meta", {})
    outputs = brief.get("outputs", {})
    assessment = brief.get("meeting_assessment", {})

    linkedin = outputs.get("linkedin", {}) or {}
    email = outputs.get("follow_up_email", {}) or {}
    press = outputs.get("press_angle", {}) or {}

    blocks = []

    # Header
    title = meta.get("meeting_title", "Untitled")[:140]
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"📋 Meeting brief — {title}"},
    })

    # Meta context
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"*Date:* {meta.get('meeting_date', 'unknown')}"},
            {"type": "mrkdwn", "text": f"*Attendees:* {', '.join(meta.get('attendees', []))}"},
        ],
    })

    # Publishability note
    if assessment.get("reasoning"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*✅ Publishable:* yes — _{assessment.get('reasoning')}_",
            },
        })

    blocks.append({"type": "divider"})

    # LinkedIn block
    if linkedin.get("text"):
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": f"LinkedIn draft ({linkedin.get('launch_stage', '')})"},
        })
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": linkedin["text"]},
        })
        ctx = [{"type": "mrkdwn", "text": f"_{linkedin.get('reasoning', '')}_"}]
        if linkedin.get("hashtags"):
            ctx.append({"type": "mrkdwn", "text": f"*Hashtags:* {' '.join(linkedin['hashtags'])}"})
        blocks.append({"type": "context", "elements": ctx})
        blocks.append({"type": "divider"})

    # Email block
    if email.get("body"):
        recipient = email.get("to_name", "")
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": f"Email draft ({email.get('launch_stage', '')}) → {recipient}"},
        })
        body_text = (
            f"*Subject:* {email.get('subject', '')}\n\n"
            f"```\n{email.get('body', '')}\n```"
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": body_text},
        })
        ctx_elements = [{"type": "mrkdwn", "text": f"_{email.get('reasoning', '')}_"}]
        alternates = email.get("alternate_recipients") or []
        if alternates:
            alt_text = " · ".join(a.get("name", "?") for a in alternates)
            ctx_elements.append({"type": "mrkdwn", "text": f"*Alt recipients:* {alt_text}"})
        blocks.append({"type": "context", "elements": ctx_elements})
        blocks.append({"type": "divider"})

    # Press angle block
    if press.get("headline"):
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": f"Press angle ({press.get('launch_stage', '')})"},
        })
        bullets = "\n".join(f"• {pt}" for pt in press.get("supporting_points", []))
        text = f"*{press['headline']}*\n\n{bullets}"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        })
    ctx_elements = [
        {"type": "mrkdwn", "text": f"_{press.get('reasoning', '')}_"},
        {"type": "mrkdwn", "text": f"*Target:* {press.get('target_publication_type', '')}"},
    ]
    if linear_url:
        ctx_elements.append({
            "type": "mrkdwn",
            "text": f"*Tracked in Linear:* <{linear_url}|{linear_id}>",
        })
    elif linear_error:
        ctx_elements.append({
            "type": "mrkdwn",
            "text": f"*⚠ Linear filing failed:* `{linear_error[:100]}` — file manually",
        })
    blocks.append({"type": "context", "elements": ctx_elements})

    # Review checklist
    checklist = brief.get("review_checklist", [])
    if checklist:
        bullets = "\n".join(f"• {item}" for item in checklist)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Before you ship — verify:*\n{bullets}",
            },
        })

    return blocks


def post_to_slack(blocks: list, fallback_text: str) -> str:
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL_ID")
    if not token or not channel:
        raise ValueError("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set.")

    client = WebClient(token=token)
    try:
        resp = client.chat_postMessage(channel=channel, blocks=blocks, text=fallback_text)
        return resp["ts"]
    except SlackApiError as e:
        raise RuntimeError(f"Slack post failed: {e.response['error']}") from e


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python handoff_agent.py <path_to_brief.json>", file=sys.stderr)
        return 1

    brief_path = sys.argv[1]
    try:
        with open(brief_path, "r", encoding="utf-8") as f:
            brief = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"✗ Failed to read brief: {e}", file=sys.stderr)
        return 2

    meta = brief.get("meta", {})
    assessment = brief.get("meeting_assessment", {})

    print(f"→ Routing brief from: {brief_path}", file=sys.stderr)

    # Branch on publishability
    if not assessment.get("is_publishable", True):
        print("⊘ Meeting marked not publishable. Posting skip notice...", file=sys.stderr)
        try:
            blocks = build_skip_blocks(meta, assessment)
            ts = post_to_slack(blocks, f"Meeting skipped: {meta.get('meeting_title', 'Untitled')}")
            print(f"✓ Skip notice posted (ts={ts})", file=sys.stderr)
            return 0
        except Exception as e:
            print(f"✗ Skip notice failed to post: {e}", file=sys.stderr)
            return 2

    # Publishable path — Linear first, then Slack
    linear_url, linear_id, linear_error = None, None, None
    press = brief.get("outputs", {}).get("press_angle", {}) or {}

    if press.get("headline"):
        print("→ Creating Linear issue for press angle...", file=sys.stderr)
        try:
            linear_url, linear_id = create_linear_issue(press, meta)
            print(f"  ✓ Linear: {linear_id} — {linear_url}", file=sys.stderr)
        except Exception as e:
            linear_error = str(e)
            print(f"  ✗ Linear filing failed: {e}", file=sys.stderr)
            print("  → Continuing to Slack without Linear link", file=sys.stderr)

    # Slack is critical — if it fails, the operator never sees the brief
    print("→ Posting unified brief to Slack...", file=sys.stderr)
    try:
        blocks = build_brief_blocks(brief, linear_url, linear_id, linear_error)
        ts = post_to_slack(blocks, f"Meeting brief: {meta.get('meeting_title', 'Untitled')}")
        print(f"  ✓ Brief posted to Slack (ts={ts})", file=sys.stderr)
    except Exception as e:
        print(f"  ✗ Slack post failed: {e}", file=sys.stderr)
        if linear_url:
            print(f"  ⚠ Linear issue {linear_id} exists but no Slack notification went out.", file=sys.stderr)
            print(f"    Manual follow-up: {linear_url}", file=sys.stderr)
        return 2

    # Exit code reflects partial vs full success
    if linear_error:
        print("⚠ Handoff complete with partial failure (Linear). Slack message includes a manual-file note.", file=sys.stderr)
        return 1
    print("✓ Handoff complete.", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())