# Demo video script v4 (separated: Speaker / Doer / Screen)

Target 2:45, hard ceiling 3:00. Beats 1-6 sync all three sections. Flub a line? Pause two seconds, repeat the sentence, keep rolling.

---

# PART 1 - SPEAKER SCRIPT (read this top to bottom, nothing else)

**[Beat 1]**
"This is Inspection Autopilot, running live on Alibaba Cloud with real data: 1,333 restaurant inspections from Clayton County, Georgia. Before I show you the product, here's the proof it works. We replayed the county's own history, 350 real next-inspection outcomes. Facilities this agent flags URGENT went on to fail their next real inspection 68 percent of the time. Facilities it clears: 21 percent. The future agreed with the triage."

**[Beat 2]**
"That badge means every response you're about to see is live qwen-plus, nothing canned. I'm clicking Run: the agent is now reading five real inspection records, scores, violations, correction status, facility history, and making two structured passes on each: first a risk triage that must cite the violation lines word for word, then drafting the actual follow-up actions. Code checks every citation against the official record; anything the model can't back up gets dropped and counted."

**[Beat 3]**
"Golden Krust. Score 71, two uncorrected priority violations, handwashing and cold holding. The agent flagged it urgent."

"Every claim is a citation copied verbatim from the record, and code verified each one."

"It drafted the enforcement letter, and look at this badge: every violation code the letter names was machine-checked against the official record before any human saw it. If the model ever names a violation that isn't in the record, it gets flagged right here, above the approve button."

"And this is the exact fact sheet the agent read, so anyone can audit any citation in one click."

"The agent proposes. A person disposes. I'm approving the re-inspection."

**[Beat 4]**
"And approval isn't a checkbox. Golden Krust just became first on next week's inspector route, dated, risk-ordered, with the address. That's the work order a county actually runs its day on. Nothing reaches this schedule without a human signature."

**[Beat 5]**
"We measure this system instead of trusting it. Zero hallucinated citations across the live eval, including 28 deliberately dangerous inspections, none of which were triaged routine. But zero could just mean the alarm never rings. So we forged fifty citations ourselves, half invented, half real violation text stolen from other inspections. The validator caught all fifty and kept all seventy-five legitimate ones. We know the tripwire works because we set it off."

**[Beat 6]**
"Live governance numbers, straight from an append-only log: human agreement rate, citations dropped, decisions are final. Exactly one rule can skip the queue, acknowledging spotless routine inspections, and it's printed right on the page. Inspection Autopilot: Qwen on Alibaba Cloud, open source, MIT, and live at this URL right now. Click Run yourself. The agent does the paperwork. People keep the authority."

---

# PART 2 - DOER RUN SHEET (your hands; each action fires on its cue word)

**Beat 1** (0:00-0:20)
1. Start on the top of the page, tiles filling the view. Touch nothing.
2. While saying "68 percent": rest cursor under the 68% tile. On "21 percent": move to the 21% tile.

**Beat 2** (0:20-0:50)
3. On "That badge": point at the green LIVE: qwen-plus badge (top right).
4. On "I'm clicking Run": click **Run agent on next 5 inspections**. Button shows "Agent running..." ~30 seconds; the speaker lines cover the wait.
5. When the status line appears ("Triaged 5 ..."), point at it briefly.

**Beat 3** (0:50-1:40)
6. Scroll the queue to the **Golden Krust** letter card (red URGENT pill).
7. On "Score 71": point at the score in the rationale text.
8. On "citation copied verbatim": run the cursor slowly down the cited violation bullets.
9. On "It drafted the enforcement letter": point at the gray letter box, then the green badge below it.
10. On "the exact fact sheet": click **Source inspection record (what the agent read)**, let it expand, pause two seconds, click again to collapse.
11. On "I'm approving": find Golden Krust's **schedule_reinspection** card (adjacent) and click **Approve**.

**Beat 4** (1:40-1:55)
12. Click the **Re-inspection schedule** tab. Golden Krust is at the top under its due date.
13. On "with the address": underline the street address with the cursor.

**Beat 5** (1:55-2:25)
14. On "We measure": Alt-Tab to the black eval window.
15. On "Zero hallucinated": point at `citation_hallucination_rate: 0.0` and `n_dangerous_checked: 28` (scroll up if needed).
16. On "forged fifty citations": scroll down to the sabotage report; point at `forged_citations_caught: 50`, then `legitimate_citations_preserved: 75`.

**Beat 6** (2:25-2:45)
17. On "Live governance numbers": Alt-Tab back to the browser, Approval queue.
18. Run the cursor across the stat chips left to right.
19. On "Exactly one rule": point at the automation-rules line under the chips.
20. On "live at this URL": move the cursor up to the address bar. Hold still until you finish speaking. Stop recording.

---

# PART 3 - SCREEN CHECKLIST (verify before recording + at each beat)

Pre-flight:
- Browser: http://47.82.181.199:8080, 100% zoom, bookmarks bar hidden, notifications off, shield favicon visible in the tab
- Queue holds 5 ELEVATED cards (seeded batch); schedule tab EMPTY (fills when you approve on camera)
- Eval window open with both reports (from run-evals.cmd), font enlarged
- OBS: Display Capture + mic, meter peaks upper yellow at video volume, 10s test played back audibly
- This script on phone/print, NOT on the recorded screen

Per beat:
- B1: three % tiles visible at top; LIVE badge top right
- B2: Run button visible before click; status line after
- B3: Golden Krust card shows URGENT pill, citations list, letter, green "letter cross-checked" badge; expect it in the newly arrived batch (if it lands ELEVATED, say "elevated" instead of "urgent"; everything else unchanged)
- B4: schedule tab shows Golden Krust with due date + address
- B5: eval window shows both JSON reports, text readable at 1080p
- B6: stat chips populated (proposals, pending, decisions, agreement); rules line visible

After recording: watch once (audio, under 3:00, LIVE badge visible in B2-B4) -> YouTube upload as Public, title "Inspection Autopilot - Qwen Cloud Hackathon Demo (Track 4)" -> send the link.
