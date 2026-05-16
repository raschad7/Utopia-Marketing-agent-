"""
primary_agent.py — Utopia LAUNCH brief generator (two-stage)

Stage 1: cheap gate (gpt-4o-mini) — decides publishability, extracts metadata
Stage 2: full writer (gpt-4o) — drafts the three outputs, only if publishable

Skipping the writer on non-publishable meetings saves tokens, lowers latency,
and keeps responsibilities separate (gate decides, writer drafts).

Usage:
    python primary_agent.py not_xxxxx
    python primary_agent.py samples/input_transcript.txt
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from granola_client import GranolaClient, load_local_transcript, transcript_to_text

load_dotenv()

AGENT_VERSION = "launch-brief-v0.2"
GATE_MODEL = "gpt-4o-mini"
WRITER_MODEL = "gpt-4o"
SKILL_PACK = (
    Path(__file__).parent
    / "utopia-skills"
    / "utopia-studio-cobuild-gtm-launch-brief"
)
PROMPT_PATH = SKILL_PACK / "launch-brief-writer" / "SKILL.md"
GATE_PROMPT_PATH = SKILL_PACK / "meeting-publishability-gate" / "SKILL.md"
FACTS_PATH = SKILL_PACK / "launch-brief-writer" / "studio-facts.md"

OUTPUTS_DIR = Path(__file__).parent / "outputs"


def load_system_prompt() -> str:
    """Writer system prompt (LAUNCH brief) + studio facts."""
    base = PROMPT_PATH.read_text(encoding="utf-8")
    facts = FACTS_PATH.read_text(encoding="utf-8")
    return f"{base}\n\n---\n\n{facts}"


def load_gate_prompt() -> str:
    """Gate system prompt — focused on publishability decision only."""
    return GATE_PROMPT_PATH.read_text(encoding="utf-8")


def fetch_transcript(source: str) -> dict:
    """Fetch from Granola API or local file. Returns {id, title, transcript_text}."""
    if source.startswith("not_"):
        client = GranolaClient()
        note = client.get_note(source, include_transcript=True)
        return {
            "id": note["id"],
            "title": note.get("title", "Untitled meeting"),
            "transcript_text": transcript_to_text(note),
        }
    return load_local_transcript(source)


def gate_meeting(transcript_text: str) -> dict:
    """Stage 1: cheap publishability gate. Returns gate decision + basic metadata."""
    client = OpenAI()
    response = client.chat.completions.create(
        model=GATE_MODEL,
        temperature=0.3,  # more deterministic for binary decision
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": load_gate_prompt()},
            {"role": "user", "content": transcript_text},
        ],
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Gate model returned empty response content")
    return json.loads(content)


def call_writer(transcript_text: str) -> dict:
    """Stage 2: full writer. Drafts the three outputs + key moments."""
    client = OpenAI()
    response = client.chat.completions.create(
        model=WRITER_MODEL,
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": transcript_text},
        ],
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Writer model returned empty response content")
    return json.loads(content)


def build_skip_brief(gate_result: dict) -> dict:
    """Build a minimal brief for the skip case — enough for handoff to post notice."""
    return {
        "meta": {
            "meeting_title": gate_result.get("meeting_title", "Untitled"),
            "meeting_date": gate_result.get("meeting_date", ""),
            "attendees": gate_result.get("attendees", []),
        },
        "meeting_summary": {
            "tldr": gate_result.get("summary_tldr", ""),
            "topics_discussed": [],
            "decisions_made": [],
            "action_items": [],
        },
        "meeting_assessment": {
            "is_publishable": False,
            "reasoning": gate_result.get("reasoning", ""),
        },
        "key_moments": [],
        "outputs": {
            "linkedin": {"text": None},
            "follow_up_email": {"body": None},
            "press_angle": {"headline": None},
        },
        "review_checklist": [],
    }


def generate_brief_from_transcript(transcript_text: str) -> dict:
    """Run both stages and return the final brief (publishable or skipped)."""
    print(f"→ Stage 1: gating publishability ({GATE_MODEL})", file=sys.stderr)
    gate_result = gate_meeting(transcript_text)
    is_pub = gate_result.get("is_publishable", False)
    print(f"  Gate: is_publishable={is_pub}", file=sys.stderr)
    print(f"  Reasoning: {gate_result.get('reasoning', '')}", file=sys.stderr)

    if not is_pub:
        print("⊘ Skipping writer stage — meeting not publishable", file=sys.stderr)
        return build_skip_brief(gate_result)

    print(f"→ Stage 2: drafting content ({WRITER_MODEL})", file=sys.stderr)
    brief = call_writer(transcript_text)
    # Gate is authoritative — overwrite the writer's own assessment
    brief["meeting_assessment"] = {
        "is_publishable": True,
        "reasoning": gate_result.get("reasoning", ""),
    }
    return brief


def attach_runtime_meta(brief: dict, source_id: str) -> dict:
    """Fill meta fields the LLM doesn't generate (timestamps, source, version)."""
    brief.setdefault("meta", {})
    brief["meta"]["transcript_source"] = source_id
    brief["meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    brief["meta"]["agent_version"] = AGENT_VERSION
    return brief


def save_brief(brief: dict) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUTS_DIR / f"brief_{stamp}.json"
    path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python primary_agent.py <granola_note_id | transcript_file>",
              file=sys.stderr)
        return 1

    source = sys.argv[1]
    print(f"→ Fetching transcript from: {source}", file=sys.stderr)
    transcript = fetch_transcript(source)

    brief = generate_brief_from_transcript(transcript["transcript_text"])
    brief = attach_runtime_meta(brief, transcript["id"])
    output_path = save_brief(brief)

    print(f"✓ Brief saved to: {output_path}", file=sys.stderr)
    print(output_path)  # stdout for piping
    return 0


if __name__ == "__main__":
    sys.exit(main())