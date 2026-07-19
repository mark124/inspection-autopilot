# Devpost submission draft

**Track:** Track 4, Autopilot Agent
**Project name:** Inspection Autopilot

## Inspiration

County environmental health offices are chronically understaffed. Inspectors file reports, and then the follow-up work piles up: deciding which facilities need a recheck, drafting violation letters, ordering the queue. It is repetitive, judgment-adjacent work, exactly what an agent should draft and a human should approve. We built the autopilot for that back office on real data: 1,333 actual inspections and 3,579 violation records from Clayton County, Georgia's public health portal.

## What it does

New inspection results flow in. For each one, a Qwen agent reads the full record (score, violations with priority and repeat flags, correction status, facility history) and triages follow-up risk into URGENT, ELEVATED, or ROUTINE, with a rationale that must cite the actual violation lines verbatim. A second pass drafts the concrete next steps: a re-inspection with a proposed window, or a formal follow-up letter naming the specific violations.

Then the governance kicks in, in layers. Code validates every citation against the record and drops what does not match (dropped citations are counted, so the hallucination rate is a measured number). A deterministic linter cross-checks every violation code a drafted letter names against the official record and badges mismatches right above the Approve button. Every consequential action then waits in a human approval queue, where the supervisor can open the exact fact sheet the agent read before deciding. Decisions are final, inserted into an append-only log. Approved re-inspections roll up into a dated, risk-ordered inspector schedule: the approval click produces the work order a county actually runs its week on. Exactly one narrow automation rule may skip the queue, and the UI lists it.

## The receipts

Did the agent's judgment hold up? We replayed the county's own history: 350 real (inspection, next inspection) pairs, triaged live by qwen-plus using only time-T information. Facilities the agent flagged URGENT failed their next real inspection 67.6% of the time. Facilities it cleared as ROUTINE failed only 21.1%, against a 48.6% base rate. The future agreed with the triage.

And because a validator that never fires is indistinguishable from one that does not work, we sabotaged our own agent: 50 forged citations injected (half invented, half real violation text lifted from other inspections). The validator caught 50 of 50 and preserved all 75 legitimate citations.

## How we built it

- Qwen (qwen-plus) on Alibaba Cloud Model Studio via the OpenAI-compatible DashScope endpoint, two structured-JSON agent passes per inspection
- Deterministic verification layers around the model: citation validator with a measured 0.0% hallucination rate across 126 citations on the committed live eval (50 inspections, 28 of them stratified dangerous cases), letter linter, input validation on every write path
- FastAPI backend deployed on Alibaba Cloud ECS, SQLite insert-only store, dependency-free single-page UI
- Hardened for a 3-week unattended public deployment: bounded model timeouts, per-inspection error isolation with a circuit breaker, a single-flight run lock, and a daily run budget

## Challenges

Grounding, honestly measured. An agent that invents violations in an official letter is worse than no agent. We solved it structurally (verbatim-citation contract, code-side validation, deterministic letter linting) and then proved the tripwire works by attacking it ourselves.

## What we're proud of

The governance pattern: agent proposes, human disposes, the log is append-only, automation is explicit, and every claim on screen is a measured number backed by a committed eval report.

## What's next

Complaint intake as a second trigger, per-inspector routing on the schedule, and piloting with a Georgia county.
