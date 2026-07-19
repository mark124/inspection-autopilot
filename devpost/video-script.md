# 3-minute demo video script (v2, post-hardening)

Target: 2:50 runtime. Screen recording + voiceover. 1080p, live mode ONLY (green "LIVE: qwen-plus" badge visible in every UI shot).

## Shot list

**0:00-0:18 | The problem (title card + one data slide)**
"This is real inspection data from Clayton County, Georgia. 309 food facilities, 1,333 inspections, 3,579 violations. Every one needs a follow-up decision: who gets a recheck, who gets a letter, who's fine. That back-office work is where critical violations slip through."

**0:18-0:40 | The receipts (Outcomes tiles, top of the UI)**
"Before anything else, the proof. We replayed the county's own history, 350 real next-inspection outcomes, triaged live by Qwen using only what was knowable at the time. Facilities it flagged URGENT failed their next real inspection 68 percent of the time. Facilities it cleared: 21 percent, against a 49 percent base rate. The future agreed with the triage."

**0:40-1:40 | Live demo (the core minute)**
- Click "Run agent on next 5 inspections". Point at the LIVE badge and the status line ("Triaged 5 · N remaining").
- Pick an ELEVATED card: "84 score, an uncorrected priority violation, and the agent cites the exact handwashing line from the record."
- Expand "Source inspection record": "This is the fact sheet the agent read. Check any citation against it, one click."
- Open a drafted letter, point at the green badge: "The letter itself is machine-verified: every violation code it names is cross-checked against the official record before a human ever sees it. A mismatch gets flagged right above the approve button."
- Approve the re-inspection, reject something else: "The agent proposes. A person disposes. Decisions are final, in an append-only log."
- Cut to the Schedule tab: "And approval isn't a checkbox. That facility is now first on next week's inspector queue, with a due date. That's the work order a county runs its day on."

**1:40-2:10 | Sabotage + evals (terminal)**
Run `python -m evals.eval_triage --sabotage 25` on screen.
"Zero measured hallucinations could just mean the alarm never rings. So we forged fifty citations ourselves, half invented, half real violation text stolen from other inspections. It caught all fifty and preserved every legitimate one. We know the tripwire works because we set it off."
Then flash `--n 25 --dangerous 25` report: "On 28 deliberately dangerous inspections: zero triaged routine."

**2:10-2:30 | Trust strip + governance**
Pan the stat chips: "Agreement rate, citations dropped, tier mix, live from the append-only log. One automation rule can skip the queue, it's printed right here, and it only touches clean routine inspections."

**2:30-2:50 | Deployment + close (Alibaba console + repo)**
"Backend on Alibaba Cloud ECS, Qwen through Model Studio. Open source, MIT, and live at this URL right now: click Run yourself. This is governed autonomy for a county that can't afford mistakes: the agent does the paperwork, people keep the authority."

## Recording checklist
- .env has the real key; /api/health shows mode "live" before recording
- Reset autopilot.db before the take so the queue starts empty (rm the file, restart)
- First batch should contain an ELEVATED case with an uncorrected priority violation and a letter (check beforehand; 12 Lunar Asian Eatery's 07-06-2026 inspection is ideal if unprocessed)
- OBS or Xbox Game Bar; mic check; no bookmarks bar; 100% browser zoom
