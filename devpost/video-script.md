# 3-minute demo video script

Target: 2:45 runtime. Screen recording + voiceover. Record at 1080p, live mode ONLY (green "LIVE: qwen-plus" badge visible in every UI shot).

## Shot list

**0:00-0:20 | The problem (title card + one data slide)**
"This is real inspection data from Clayton County, Georgia. 309 food facilities, 1,333 inspections, 3,579 violations. Every one of these needs a follow-up decision: who gets a recheck, who gets a letter, who's fine. That back-office work is why critical violations slip through."

**0:20-0:45 | The pipeline (architecture diagram)**
"Inspection Autopilot reads each new result and runs two Qwen passes on Alibaba Cloud: one triages risk with citations to the actual violation lines, one drafts the follow-up actions. Nothing invented: code verifies every citation against the record and drops what doesn't match."

**0:45-1:50 | Live demo (the core minute)**
- Click "Run agent on next 5 inspections". Point at the LIVE badge.
- Queue fills. Pick an ELEVATED case: "84 score, priority violation, and the agent cites the exact handwashing line from the record."
- Open the drafted follow-up letter: "It names the specific violations, ready for a supervisor to send."
- Approve one, reject one: "The agent proposes. A person disposes. Every decision is an insert into an append-only log, and decisions are final."
- Point at auto-approved rows: "One explicit rule skips the queue: clean routine inspections, score 90 plus, zero priority violations. That's the entire autonomous surface, and the UI lists it."

**1:50-2:20 | Evals (terminal)**
Run `python -m evals.eval_triage --n 25` on screen.
"We don't assume the agent is grounded, we measure it: citation hallucination rate, and two hard invariants. No dangerous inspection may be triaged routine, and actions must match the tier."

**2:20-2:45 | Deployment + close (Alibaba console + repo)**
"Backend on Alibaba Cloud ECS, Qwen through Model Studio. Open source, MIT. This is what governed autonomy looks like for a county that can't afford mistakes: the agent does the paperwork, people keep the authority."

## Recording checklist
- .env has the real key; /api/health shows mode "live" before recording
- Reset autopilot.db before the take so the queue starts empty
- Have one URGENT-looking facility in the first batch (check beforehand which batch contains a low score; adjust batch size so it appears)
- OBS or Xbox Game Bar; mic check; no browser bookmarks bar
