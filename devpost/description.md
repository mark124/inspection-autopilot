# Devpost submission draft

**Track:** Track 4, Autopilot Agent
**Project name:** Inspection Autopilot

## Inspiration

County environmental health offices are chronically understaffed. Inspectors file reports, and then the follow-up work piles up: deciding which facilities need a recheck, drafting violation letters, reordering the queue. It is repetitive, judgment-adjacent work, exactly what an agent should draft and a human should approve. We built the autopilot for that back office, and we built it on real data: 1,333 actual inspections and 3,579 violation records from Clayton County, Georgia's public health portal.

## What it does

New inspection results flow in. For each one, a Qwen agent reads the full record (score, violations with priority and repeat flags, correction status, facility history) and triages follow-up risk into URGENT, ELEVATED, or ROUTINE, with a rationale that must cite the actual violation lines. A second agent pass drafts the concrete next steps: a re-inspection with a proposed window, a formal follow-up letter naming the specific violations, or a routine acknowledgment.

Then the governance kicks in. Every consequential action lands in a human approval queue. A supervisor sees the tier, the cited evidence, and the drafted letter, and approves or rejects with one click. Exactly one narrow automation rule may skip the queue (acknowledging a clean, high-scoring routine inspection), and the UI lists it. Every proposal and every decision is an insert into an append-only log; decisions are final and source records are never mutated.

## How we built it

- Qwen (qwen-plus) on Alibaba Cloud Model Studio via the OpenAI-compatible DashScope endpoint, two structured-JSON agent passes per inspection
- Code-side citation validation: any cited violation that does not match the record is dropped and counted, so the hallucination rate is measured, not assumed
- FastAPI backend deployed on Alibaba Cloud ECS, SQLite insert-only store, dependency-free single-page UI
- An eval harness with hard invariants: no inspection with an uncorrected priority violation and a score under 85 may be triaged ROUTINE, and drafted actions must match the assigned tier

## Challenges

Grounding. An agent that invents violations in an official letter is worse than no agent. We solved it structurally: the model must copy violation text verbatim to cite it, code verifies every citation against the record, and the eval reports the measured hallucination rate on every run.

## What we're proud of

The governance pattern: agent proposes, human disposes, log is append-only, automation is explicit and narrow. That is what it takes for a real county to actually adopt this.

## What's next

Complaint intake as a second trigger, inspector queue optimization, and piloting with a Georgia county.
