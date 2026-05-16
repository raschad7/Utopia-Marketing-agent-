"""
Minimal Granola Personal API client.

Wraps the two endpoints we need for this agent: list notes (for discovery)
and get a single note with its transcript (the one we actually call).

Granola's transcript format is a list of utterances tagged by audio source
(microphone or system), not by speaker name. The LLM maps speakers using the
meeting context — works well enough for a 3-person studio meeting.

Docs: https://docs.granola.ai/introduction
"""

import os
from typing import Optional

import requests

GRANOLA_BASE_URL = "https://public-api.granola.ai/v1"


class GranolaClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GRANOLA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GRANOLA_API_KEY not set. Add it to your .env file."
            )
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def list_notes(self, created_after: Optional[str] = None,
                   cursor: Optional[str] = None) -> dict:
        """List your notes. created_after is ISO8601, cursor is for pagination."""
        params = {}
        if created_after:
            params["created_after"] = created_after
        if cursor:
            params["cursor"] = cursor
        r = self.session.get(f"{GRANOLA_BASE_URL}/notes", params=params)
        r.raise_for_status()
        return r.json()

    def get_note(self, note_id: str, include_transcript: bool = True) -> dict:
        """Fetch a single note by its `not_` ID, optionally with transcript."""
        params = {"include": "transcript"} if include_transcript else {}
        r = self.session.get(
            f"{GRANOLA_BASE_URL}/notes/{note_id}",
            params=params,
        )
        r.raise_for_status()
        return r.json()


def transcript_to_text(note: dict) -> str:
    """Turn a Granola note (with transcript array) into plain readable text
    the LLM can consume."""
    lines = []
    title = note.get("title", "")
    if title:
        lines.append(f"Meeting: {title}\n")

    for utterance in note.get("transcript") or []:
        source = utterance.get("speaker", {}).get("source", "unknown")
        text = (utterance.get("text") or "").strip()
        if not text:
            continue
        # Granola tags by audio source, not speaker name. Label as You/Other.
        label = "You" if source == "microphone" else "Other"
        lines.append(f"{label}: {text}")

    return "\n".join(lines)


def load_local_transcript(path: str) -> dict:
    """Fallback: load a transcript from disk for testing.

    Returns the same shape that fetch_transcript() expects downstream.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    basename = os.path.basename(path)
    return {
        "id": f"file:{basename}",
        "title": os.path.splitext(basename)[0].replace("_", " "),
        "transcript_text": text,
    }