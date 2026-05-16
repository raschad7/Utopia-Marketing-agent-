# utopia-studio-cobuild-gtm-launch-brief

A skill pack for Utopia Studio's Co-Build M7 (Go-to-Market) module. Turns a
Granola meeting transcript into a complete content brief — LinkedIn post,
follow-up email, and press angle — ready for the marketing team to review
and ship.

## What's in this pack

Two composable skills:

### `meeting-publishability-gate`
A binary classifier that decides whether a meeting transcript contains
content worth drafting. Designed to run on a fast/cheap model
(`gpt-4o-mini`) as the first stage of a two-stage pipeline. Returns
basic metadata plus `is_publishable` and reasoning.

### `launch-brief-writer`
The main creative skill. Given a publishable transcript, produces a
structured JSON brief with three outputs mapped to the LAUNCH framework:
- LinkedIn post (Amplify stage)
- Personalised follow-up email (Nurture stage)
- One-line press angle with supporting points (Convert stage)

Plus key moments, reasoning, and a review checklist.

## Composition

The gate runs first; the writer is invoked only if the gate returns
`is_publishable: true`. This separates fast classification from
expensive creative work, and lets each prompt iterate independently.

## How to install

Drop this folder into the Utopia Studio skills repository:

\`\`\`
The-Utopia-Studio/skills/utopia-studio-cobuild-gtm-launch-brief/
\`\`\`

Or load via Claude Code's skill installation pattern. Compatible with
Claude Code, Cursor, and any client that loads SKILL.md context.

## Studio facts

`launch-brief-writer/studio-facts.md` carries the studio's factual context
(QDB backing, fund structure, people, partnerships). It is injected
alongside the writer prompt at runtime. Update it as studio facts
evolve — no prompt edits needed.

## License

MIT.