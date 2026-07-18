# Blog post draft (for the Blog Post Award, publish on dev.to or Medium, link in submission)

Title: The agent proposes, the human disposes: building a food-safety autopilot on Qwen

When people demo "agents that automate business workflows," the demo usually ends right where the real problem begins: the moment the agent's output touches the real world. A wrong chatbot answer is annoying. A wrong official violation letter to a restaurant, sent under a county's letterhead, is a lawsuit.

For the Qwen Cloud hackathon I built Inspection Autopilot, an agent that does the follow-up paperwork for a county food-safety office, on real public data: 1,333 inspections and 3,579 violation records from Clayton County, Georgia. And the interesting part is not the agent. It's the governance around it.

## Three design rules

**1. Citations are verified in code, not vibes.** The triage agent must justify every risk call by citing violation lines from the inspection record, copied verbatim. The backend then checks every citation against the source record. Anything that doesn't match gets dropped and counted. The eval harness reports the measured hallucination rate on every run, so "the agent is grounded" is a number, not a hope.

**2. The log is append-only.** Proposals and decisions are insert-only tables. A supervisor's decision is final; there is no update path, and the source inspection data is never mutated. If you want an audit trail a county can trust, the schema has to make tampering structurally impossible, not just discouraged.

**3. Automation is explicit and narrow.** Exactly one rule may bypass the human queue: acknowledging a clean routine inspection with a score of 90 or above and zero priority violations. The UI lists the rule. Everything else, every recheck, every letter, waits for a human click.

## The Qwen part

Two structured-JSON passes per inspection through Model Studio's OpenAI-compatible endpoint (qwen-plus, temperature 0.2, response_format json_object). Pass one triages risk with citations. Pass two drafts the actions: a re-inspection window, or a formal letter that names the specific violations and the correction expected. The JSON contract plus code-side validation means a malformed or ungrounded response degrades to a smaller proposal set, never to an invented fact in an official document.

## What I'd tell anyone building "autopilot" agents

Your demo should show a rejection. Seriously. The moment a human clicks "reject" and the system records it permanently is the moment the workflow becomes adoptable by an organization with actual liability. Autonomy you can't override is a liability; autonomy with a paper trail is a product.

Repo (MIT): [link]
Live demo: [link]
