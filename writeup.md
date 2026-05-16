## Operator & problem

Utopia Studio's Marketing & Events lead needs this during M7 Go-to-Market. After every content-worthy studio meeting, they manually read the Granola transcript and draft a LinkedIn post, a follow-up email, and a press angle. That costs 35-45 minutes per meeting, delays publishing, and makes the studio voice depend on whoever has time that week.

## The agent

Utopia Launch Brief turns a Granola transcript into a ready-to-review content brief. It takes a Granola note ID or local transcript file, runs a publishability gate, then drafts three LAUNCH outputs: LinkedIn, email, and press angle. It produces machine-readable JSON, posts the operator version to Slack, and creates a Linear issue for the press angle. It calls OpenAI, Granola Personal API, Slack Web API, and Linear GraphQL.

## Sample input

```text
[Meeting: Radical Asia weekly pipeline - 2026-05-13 - 35 min]
[Attendees: Karan Pinto, Alina Truhina, Sophia Tan, Priya Krishnan]

Sophia: The one I want to focus on is a B2B SaaS for cold-chain logistics in Indonesia. Indonesia loses an estimated 30% of fresh agricultural output to cold-chain failures every year.
Sophia: Real-time temperature monitoring with predictive failure alerts. The predictive model is trained on Indonesian-specific climate data and infrastructure conditions.
Alina: That's a perfect Global South AI thesis. Adapting models to local conditions, not deploying Silicon Valley AI in a context it wasn't built for.
Alina: We got an inbound from a Nikkei Asia reporter writing a piece on AI venture studios in the Global South. Her name is Akiko Tanaka.
Karan: Give her one specific story rather than a portfolio overview. Reporters do better with a single narrative than a generic studio pitch.
```

## Sample output

```text
Meeting brief - Radical Asia weekly pipeline
Date: 2026-05-13
Attendees: Karan Pinto, Alina Truhina, Sophia Tan, Priya Krishnan
Publishable: yes - contains a 30% market failure metric, a local-AI thesis, and a named journalist opportunity.

LinkedIn draft (Amplify)
Indonesia loses 30% of fresh agricultural output to cold-chain failures every year. The interesting part is not the dashboard. It is the model: predictive alerts trained on Indonesian climate and infrastructure conditions. Global South AI will not be won by exporting Silicon Valley defaults. It will be won by building for the local operating reality.

Email draft (Nurture) -> Sophia Tan
Subject: Jakarta cold-chain SaaS next steps
Sophia, the Indonesia cold-chain thesis is the clearest story from today's pipeline call: 30% annual agricultural loss, existing hardware, and a software-only wedge. Alina will send Adi the M1 pre-read before the discovery call. Please send the customer-pilot details before then so we can pressure-test the market proof. - Karan

Press angle (Convert)
AI models built for local operating conditions are becoming the wedge for Global South infrastructure markets.
Tracked in Linear: MAR-2
```

## What you cut

- Full Slack slash-command interface. It is the best operator UX, but it needs webhook hosting, Slack signing verification, and deployment time.
- Multi-agent specialist chain. Separate LinkedIn, email, and press agents would improve quality, but the two-stage gate plus writer was enough for a working sample.
- Critic/editor pass. Useful, but it doubles model calls; I prioritized routing, failure handling, and a clear JSON contract.

## What broke or surprised you

- The first version emailed a person mentioned in the meeting, not an attendee. I tightened the prompt so the recipient must come from the attendee list.
- A Linear API failure originally killed the whole run. I changed the handoff so Slack still receives the brief and shows a manual filing note.
- Confidential filtering worked better as a separate gate than as one instruction inside the writer prompt.

## If you had two more days

- Add `/launch list` and `/launch run` Slack commands so the operator never touches the CLI.
- Add reaction-based approval from Slack: approve, regenerate, or file to Linear.
- Add idempotency so rerunning a transcript updates the same Slack thread and Linear issue instead of creating duplicates.
