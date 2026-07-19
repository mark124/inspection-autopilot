# Demo video script v3 (cue-card edition, matches live server state)

Target runtime: 2:45. Hard ceiling 3:00. Stumble on a line? Pause two seconds, say the sentence again, keep rolling.

## Pre-flight (all done or 2 minutes of setup)

- [x] Server reset + batch 1 seeded (5 ELEVATED cards waiting in the queue)
- [x] Eval window open with both live reports (from run-evals.cmd), font enlarged
- [ ] Browser: http://47.82.181.199:8080 open, 100% zoom, bookmarks bar hidden, notifications off
- [ ] OBS: Display Capture + mic, 1080p, 10-second test recording checked for audio
- [ ] This script printed or on a phone (NOT on the recorded screen)

Known state: your on-camera Run click delivers batch two, which includes **Golden Krust** (expect URGENT, score 71) and Date Gusto. If Golden Krust comes out ELEVATED instead of URGENT, every beat still works, just skip the word "urgent."

---

## BEAT 1 | 0:00-0:20 | The problem and the proof

**SCREEN:** Browser at the top of the page. The three percentage tiles fill the view.

**DO:** Nothing. Let the page sit. Move the cursor slowly under the 68% tile as you speak, then the 21% tile.

**SAY:** "This is Inspection Autopilot, running live on Alibaba Cloud with real data: 1,333 restaurant inspections from Clayton County, Georgia. Before I show you the product, here's the proof it works. We replayed the county's own history, 350 real next-inspection outcomes. Facilities this agent flags URGENT went on to fail their next real inspection 68 percent of the time. Facilities it clears: 21 percent. The future agreed with the triage."

## BEAT 2 | 0:20-0:50 | Run the agent, live

**SCREEN:** Same page.

**DO:** Point the cursor at the green **LIVE: qwen-plus** badge (top right) as you start. Then click **"Run agent on next 5 inspections"**. The button says "Agent running..." for ~30 seconds. KEEP TALKING through the wait; the lines below are timed to fill it.

**SAY:** "That badge means every response you're about to see is live qwen-plus, nothing canned. I'm clicking Run: the agent is now reading five real inspection records, scores, violations, correction status, facility history, and making two structured passes on each: first a risk triage that must cite the violation lines word for word, then drafting the actual follow-up actions. Code checks every citation against the official record; anything the model can't back up gets dropped and counted."

**DO:** When the status line appears ("Triaged 5 · 1,323 remaining"), point at it briefly.

## BEAT 3 | 0:50-1:40 | The Golden Krust card (the core minute)

**SCREEN:** Approval queue. Scroll until you find **Golden Krust** (follow_up_letter card).

**DO and SAY, interleaved:**

1. DO: Point at the red URGENT pill and the score in the rationale.
   SAY: "Golden Krust. Score 71, two uncorrected priority violations, handwashing and cold holding. The agent flagged it urgent."
2. DO: Slowly run the cursor down the cited violation bullets.
   SAY: "Every claim is a citation copied verbatim from the record, and code verified each one."
3. DO: Point at the gray letter draft, then the green badge under it.
   SAY: "It drafted the enforcement letter, and look at this badge: every violation code the letter names, all five, was machine-checked against the official record before any human saw it. If the model ever names a violation that isn't in the record, it gets flagged right here, above the approve button."
4. DO: Click **"Source inspection record (what the agent read)"** to expand it. Pause 2 seconds. Collapse it.
   SAY: "And this is the exact fact sheet the agent read, so anyone can audit any citation in one click."
5. DO: Find Golden Krust's **schedule_reinspection** card (right next to the letter card). Click **Approve**.
   SAY: "The agent proposes. A person disposes. I'm approving the re-inspection."

## BEAT 4 | 1:40-1:55 | Approval becomes the work order

**SCREEN/DO:** Click the **"Re-inspection schedule"** tab. Golden Krust sits at the top under its due date with its street address.

**SAY:** "And approval isn't a checkbox. Golden Krust just became first on next week's inspector route, dated, risk-ordered, with the address. That's the work order a county actually runs its day on. Nothing reaches this schedule without a human signature."

## BEAT 5 | 1:55-2:25 | Sabotage (Alt-Tab to the eval window)

**SCREEN:** Alt-Tab to the black eval window. The sabotage report (bottom one) should be visible: forged_citations_injected: 50, caught: 50.

**DO:** Point at "forged_citations_caught": 50, then scroll up briefly to the grounding report and point at "citation_hallucination_rate": 0.0 and "n_dangerous_checked": 28.

**SAY:** "We measure this system instead of trusting it. Zero hallucinated citations across the live eval, including 28 deliberately dangerous inspections, none of which were triaged routine. But zero could just mean the alarm never rings. So we forged fifty citations ourselves, half invented, half real violation text stolen from other inspections. The validator caught all fifty and kept all seventy-five legitimate ones. We know the tripwire works because we set it off."

## BEAT 6 | 2:25-2:45 | Trust strip + close

**SCREEN/DO:** Alt-Tab back to the browser, Approval queue. Run the cursor across the stat chips, then point at the automation-rules line under them.

**SAY:** "Live governance numbers, straight from an append-only log: human agreement rate, citations dropped, decisions are final. Exactly one rule can skip the queue, acknowledging spotless routine inspections, and it's printed right on the page. Inspection Autopilot: Qwen on Alibaba Cloud, open source, MIT, and live at this URL right now. Click Run yourself. The agent does the paperwork. People keep the authority."

**DO:** End on the browser with the URL visible in the address bar. Stop recording.

---

## After recording

1. Watch it once. Check: audio audible, under 3:00, LIVE badge visible in beats 2-4.
2. YouTube: upload as **Public**. Title: "Inspection Autopilot - Qwen Cloud Hackathon Demo (Track 4)". Description: one line + repo link + live URL.
3. Send the link for the final submission sweep.
