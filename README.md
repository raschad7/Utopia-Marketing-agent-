# Utopia Launch Brief

> An AI agent that turns a Granola meeting transcript into a publishable content brief — LinkedIn post, follow-up email, and press angle — delivered into the marketing team's existing tools in ~15 seconds.

Built for Utopia Studio's Marketing & Events function (Co-Build M7 — Go-to-Market). One node in the Utopia OS agent network — the JSON brief between stages is an inter-agent contract any other agent can consume.

---

## How to run it

### Setup (one-time, ~10 min)

```bash
git clone <repo>
cd utopia-launch-brief
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in your API keys (see "Tools and APIs" below)
```

### Run the agent

One end-to-end command:

```bash
# Most recent Granola meeting
python launch_brief.py --latest

# Specific Granola note ID
python launch_brief.py not_xxxxx

# Local transcript file (no Granola key needed)
python launch_brief.py samples/input_transcript.txt
```

Within ~15 seconds you'll see:
- A unified brief in `#marketing-drafts` on Slack
- A Linear issue created for the press angle, linked from the Slack message

| Flag | What it does |
|---|---|
| `--latest` | Run on the most recent Granola meeting |
| `--pick` | Numbered picker from recent Granola notes |
| `--list` | List recent Granola meetings (no agent run) |
| `--post-list` | Post the meeting list to Slack with copyable run commands |
| `--no-route` | Generate brief JSON only; skip Slack/Linear routing |

For PowerShell users — if your `.env` key isn't loading, override inline:

```powershell
$env:OPENAI_API_KEY="sk-..."
python launch_brief.py samples/input_transcript.txt
```

---

## The prompts

Two composable skills, packaged in the Utopia Studio Skills marketplace format under `utopia-skills/utopia-studio-cobuild-gtm-launch-brief/`.

### Stage 1 — `meeting-publishability-gate`

**File:** `utopia-skills/utopia-studio-cobuild-gtm-launch-brief/meeting-publishability-gate/SKILL.md`
**Model:** `gpt-4o-mini`

Binary classifier — decides whether a transcript contains content worth drafting from. Cheap, fast, focused. Skips logistics-only meetings and confidential discussions before the expensive writer call.

Output schema:
```json
{
  "meeting_title": "string",
  "meeting_date": "YYYY-MM-DD",
  "attendees": ["array of names"],
  "is_publishable": true,
  "reasoning": "one sentence",
  "summary_tldr": "one factual sentence describing the meeting"
}
```

Key rule: if uncertain, lean toward NOT publishable. False positives (forced drafts on weak meetings) hurt more than false negatives.

### Stage 2 — `launch-brief-writer`

**File:** `utopia-skills/utopia-studio-cobuild-gtm-launch-brief/launch-brief-writer/SKILL.md`
**Model:** `gpt-4o` (JSON mode)

Main creative skill. Encodes the LAUNCH framework, studio voice rules, JSON schema, hard rules, and one worked example.

Output schema (top-level fields):
```
meta              — meeting_title, date, attendees
meeting_summary   — tldr, topics_discussed, decisions_made, action_items
key_moments       — quoted moments with speaker + why_it_matters
outputs           — linkedin, follow_up_email, press_angle (each LAUNCH-tagged)
review_checklist  — verification items for the operator before publishing
```

Key rules enforced in the prompt:
- Never invent facts — reference only the transcript or `studio-facts.md`
- Email recipient must come from the attendees list (not someone merely mentioned)
- Respect in-meeting publishing gates — off the record, "keep this quiet", verbal-only consent all suppress content from drafts
- Studio voice — declarative, specific, no hedging; banned phrases enforced ("leverage", "synergy", "poised to disrupt", "operational excellence", etc.)
- LinkedIn structure — hook (≤15 words) → reveal → defensible thesis
- Prospective fellows are never named in external content until signed

`launch-brief-writer/studio-facts.md` carries the studio's factual context (people, funds, partnerships, milestones) and is injected alongside the writer prompt at runtime. Update it when studio facts evolve — no prompt edits needed.

---

## Tools and APIs

| Service | Used for | Auth |
|---|---|---|
| **OpenAI** `gpt-4o-mini` | Stage 1 publishability gate | `OPENAI_API_KEY` |
| **OpenAI** `gpt-4o` | Stage 2 LAUNCH brief writer (JSON mode) | `OPENAI_API_KEY` |
| **Granola Personal API** | Fetching meeting transcripts | `GRANOLA_API_KEY` (optional — local transcripts work without it) |
| **Slack Web API** | Posting unified briefs via Block Kit (`chat:write` scope) | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` |
| **Linear GraphQL API** | Filing press angle as a trackable issue | `LINEAR_API_KEY`, `LINEAR_TEAM_ID` |

No vector DBs. No agent frameworks. Four Python dependencies, five API integrations, ~600 lines of code.

---

## Repo structure

```
utopia-launch-brief/
├── primary_agent.py             # Stage 1 + 2: transcript → JSON brief
├── handoff_agent.py             # Router: JSON brief → Slack + Linear
├── launch_brief.py              # End-to-end orchestrator (recommended entry)
├── granola_client.py            # Minimal Granola Personal API client
├── requirements.txt
├── .env.example                 # API key template
├── samples/                     # Demo transcripts + stress-test scripts
├── outputs/                     # Runtime briefs land here (gitignored)
└── utopia-skills/               # Skill pack in Utopia Studio marketplace format
    └── utopia-studio-cobuild-gtm-launch-brief/
        ├── README.md
        ├── meeting-publishability-gate/SKILL.md
        └── launch-brief-writer/
            ├── SKILL.md
            ├── studio-facts.md
            └── examples/
```

---

## Sample transcripts

| File | Purpose |
|---|---|
| `samples/input_transcript.txt` | Canonical demo — Radical Asia pipeline meeting |
| `samples/loom_demo_qfc_milestone.txt` | Loom demo — QFC quarterly sync with a customer-win story |
| `samples/qdb_board_quarterly.txt` | Stress test — formal QDB board update with off-the-record content |
| `samples/discovery_adi_prospective.txt` | Stress test — prospective fellow, naming restrictions |
| `samples/atypical_setback_lost_fellow.txt` | Stress test — explicit gag order over a sensitive event |
| `samples/mena_legal_pack_strategy.txt` | Stress test — code-switched English/Arabic, multiple attendee types |
| `samples/logistics_only.txt` | Tests the skip path (gate returns `is_publishable: false`) |
| `samples/confidential_mix.txt` | Tests partial-confidentiality filtering |

---

## License

MIT.
