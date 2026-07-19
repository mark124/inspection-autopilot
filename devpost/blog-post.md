# Blog post draft (for the Blog Post Award, publish on dev.to or Medium, link in submission)

Title: The agent proposes, the human disposes: building a food-safety autopilot on Qwen

When people demo "agents that automate business workflows," the demo usually ends right where the real problem begins: the moment the agent's output touches the real world. A wrong chatbot answer is annoying. A wrong official violation letter to a restaurant, sent under a county's letterhead, is a lawsuit.

For the Qwen Cloud hackathon I built Inspection Autopilot, an agent that does the follow-up paperwork for a county food-safety office, on real public data: 1,333 inspections and 3,579 violation records from Clayton County, Georgia. The interesting part is not the agent. It's the governance around it, and the numbers that prove it works.

## Start with the receipts

Before trusting an agent's judgment, test it against reality. We replayed the county's own history: 350 real (inspection, next-inspection) pairs, each triaged live by qwen-plus using only information available at the time. Facilities the agent flagged URGENT went on to fail their next real inspection 67.6% of the time. Facilities it cleared as ROUTINE failed only 21.1%, against a 48.6% base rate. The tiers are not vibes; the future agreed with them.

## Three design rules

**1. Citations are verified in code, not vibes.** The triage agent must justify every risk call by citing violation lines copied verbatim from the inspection record. The backend checks every citation against the source; anything that does not match is dropped and counted. On the committed live eval (50 inspections, 28 of them deliberately dangerous cases), the measured hallucination rate is 0.0% across 126 citations.

And because a checker that never fires is indistinguishable from one that does not work, we sabotaged it: 50 forged citations injected, half invented outright, half real violation text lifted from *different* inspections, the forgery a lazy validator would miss. It caught 50 of 50 and preserved all 75 legitimate citations. We know the tripwire works because we set it off.

**2. The log is append-only.** Proposals and decisions are insert-only tables. A supervisor's decision is final; there is no update path, and the source inspection data is never mutated. If you want an audit trail a county can trust, the schema has to make tampering structurally impossible, not just discouraged.

**3. Automation is explicit and narrow.** Exactly one rule may bypass the human queue: acknowledging a clean routine inspection with a score of 90 or above and zero priority violations. The UI lists the rule. Everything else, every recheck, every letter, waits for a human click, and the drafted letter gets one more deterministic check on the way in: a linter that cross-references every violation code the letter names against the official record and flags mismatches right above the Approve button.

## The Qwen part

Two structured-JSON passes per inspection through Model Studio's OpenAI-compatible endpoint (qwen-plus, temperature 0.2, response_format json_object, bounded timeouts, per-inspection error isolation). Pass one triages risk with citations. Pass two drafts the actions: a re-inspection window, or a formal letter naming the specific violations. A malformed or ungrounded response degrades to a smaller proposal set, never to an invented fact in an official document. Approved re-inspections then roll up into a dated, risk-ordered inspector schedule, because the point of an autopilot is that the approval click produces the work order.

## What I'd tell anyone building "autopilot" agents

Your demo should show a rejection, and your eval should show an attack on your own safety layer. The moment a human clicks "reject" and the system records it permanently is the moment the workflow becomes adoptable by an organization with actual liability. Autonomy you can't override is a liability; autonomy with a paper trail and measured guardrails is a product.

Repo (MIT): https://github.com/mark124/inspection-autopilot
Live demo: [link]
