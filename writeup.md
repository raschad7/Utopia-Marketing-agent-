# Utopia Launch Brief — Writeup

## Operator & problem

The marketing & events lead at Utopia Studio — and the next AI-native 
marketing operator the studio is hiring into M7 (a role I'm interviewing 
for). After every meeting the team flags as content-worthy, they read the 
Granola transcript by hand and draft three pieces of content from scratch: 
a LinkedIn post, a personalised follow-up email, and a one-line press 
angle for the PR pipeline. Roughly 35–45 minutes per meeting, 
deprioritised when the studio gets busy, and voice-inconsistent because 
output depends on who has time that week.

## The agent

A two-stage agent. A cheap publishability gate (`gpt-4o-mini`, ~2s) 
decides whether a meeting is worth drafting and filters confidential 
content. A writer (`gpt-4o`, JSON-mode, ~8s) drafts three outputs mapped 
to the LAUNCH framework — LinkedIn post (Amplify), follow-up email 
(Nurture), and press angle (Convert) — plus key moments and a review 
checklist. Input: a Granola Personal API note ID or a local transcript 
file. Output: one unified Slack message in `#marketing-drafts` containing 
all three drafts, plus a Linear issue for press-angle tracking. APIs 
called: OpenAI, Granola Personal API, Slack Web API, Linear GraphQL. The 
two prompt files ship as a Utopia Skills marketplace pack 
(`utopia-studio-cobuild-gtm-launch-brief`) ready to drop into 
`The-Utopia-Studio/skills/`.

## Sample input
[Meeting: Radical Asia weekly pipeline · 2026-05-13 · 35 min]
[Attendees: Karan Pinto, Alina Truhina, Sophia Tan, Priya Krishnan]
Karan: Good morning team. Let's start with the pipeline. Sophia?
Sophia: Two strong concepts this week. The one I want to focus on is
a B2B SaaS for cold-chain logistics in Indonesia. Founder is Adi
Pratama, ex-Gojek operator. Indonesia loses an estimated 30% of fresh
agricultural output to cold-chain failures every year.
Karan: 30% — that's an extraordinary number. What's the wedge?
Sophia: Real-time temperature monitoring with predictive failure alerts.
The predictive model is trained on Indonesian-specific climate data —
nobody else has that dataset.
[...full transcript at samples/input_transcript.txt]

## Sample output

The unified Slack message landing in `#marketing-drafts` ~15 seconds after trigger:
📋 Meeting brief — Radical Asia weekly pipeline
Date: 2026-05-13 · Attendees: Karan Pinto, Alina Truhina, Sophia Tan, Priya Krishnan
✅ Publishable: yes — strategic claims about Global South AI models,
a 30% market failure metric, and a named journalist contact.
──── LinkedIn draft (Amplify) ────
Indonesia loses 30% of its fresh agricultural output to cold-chain
failures. A new B2B SaaS concept aims to change that with real-time
temperature monitoring and predictive alerts, trained on local climate
data. This isn't just another AI model — it's built for Indonesia.
#globalsouth #ainative
──── Email draft (Nurture) → Sophia Tan ────
Subject: Next steps for Adi Pratama's discovery call
Sophia, great insight on the cold-chain concept. Let's move forward with
the discovery call next Tuesday or Wednesday — Alina will send Adi the
M1 pre-read. Thanks, Karan
Alt recipients: Priya Krishnan
──── Press angle (Convert) ────
AI models adapted to local Indonesian conditions aim to reduce
cold-chain failures by 30%.

Indonesia loses 30% of fresh agricultural output to cold-chain failures annually
Proprietary AI model uses Indonesian-specific climate data for predictive alerts
Targeting underserved cold-chain market with a software-only approach
Target: regional Asia press · Tracked in Linear: MAR-2

──── Before you ship — verify ────

Verify the 30% cold-chain failure statistic
Confirm Akiko Tanaka's interest aligns with the angle
Review the press headline with Karan before pitching


Full JSON at `samples/output_brief.json`.

## What you cut

- **Full Slack slash-command interface** (`/launch list`, `/launch run not_xxx`). The right operator UX, but it requires a public webhook server, Slack signing verification, and async response handling — 5+ hours with real deployment risk. Built a 20-line half-measure instead: `--post-list` posts the meeting list to Slack with copyable run commands.
- **Multi-prompt chain (Extractor → LinkedIn/Email/Press specialists).** Better per-output accuracy, but 3–4 hours of refactoring and consistency risk across drafts. Two five-line prompt patches addressed ~80% of the accuracy gap at 1/20th the cost.
- **Critic/editor pass.** A second LLM verifying each draft against voice and confidentiality rules. Doubles cost, marginal value when prompt patches and the two-stage gate already cover most of what it would catch.

## What broke or surprised you

- **The agent picked someone who wasn't in the meeting.** First run, the follow-up email was addressed to Adi Pratama — a prospective fellow *mentioned but absent*. The prompt said "key attendee"; the LLM read that as "key person discussed." Fixed by tightening to "key attendee must be in the attendees list." A literal-vs-intent gap that's a recurring LLM failure mode.
- **A Linear API failure used to kill the Slack post.** During testing, Linear briefly 401'd. The whole pipeline crashed; marketing got nothing. Refactored `handoff_agent.py` to wrap each destination in try/except, with the Slack message gracefully showing "⚠ Linear filing failed — file manually" in the press-angle section. Partial failure now degrades instead of cascading.
- **The single prompt was inconsistent on confidential content.** Originally the publishability decision lived inside the writer's prompt. Sometimes it still drafted from sensitive material (compensation, HR). Splitting into a two-stage architecture (cheap classifier → expensive writer) gave us a single-responsibility gate that's both more reliable on confidential filtering and 30x cheaper on skip cases.

## If you had two more days

1. **Full Slack slash-command + reaction-based approval.** Closes the workflow inside Slack entirely. `/launch list` → operator picks → ✓ reaction approves and ships, ↻ reaction regenerates with higher temperature. Eliminates CLI friction, which is the agent's biggest remaining UX gap.
2. **Multi-prompt chain (Extractor → specialists).** Each output gets a dedicated prompt with its own voice tuning. Improves per-output accuracy — especially key-attendee selection and named-contact press targeting — enables cheaper-model specialization, and foreshadows multi-skill orchestration as a real Utopia OS pattern. The two-stage gate is the foundation already in place.
3. **Critic pass + feedback loop.** A verifier LLM checks drafts against voice and confidentiality patterns before posting. Capture which drafts marketing edits heavily vs. ships as-is — diffs feed back into prompt iteration. Closes the "no learning" gap.