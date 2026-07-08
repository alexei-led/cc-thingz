# Problem Patterns and Thought Templates

Read when the problem type is known and you want a calibrated starting plan.

## Thought count by problem type

These are estimates — extend via `(extending plan to N)` when evidence
demands it; stop early when a thought reveals the question was wrong.

- Trivial decision (two options, clear criteria): 2–3 thoughts.
- Bug diagnosis (reproduce → isolate → fix path): 4–6 thoughts.
- Architecture decision (constraints → options → tradeoffs → verdict): 5–8 thoughts.
- Multi-constraint tradeoff (3+ competing forces): 5–8 thoughts.
- Ambiguous requirement (missing info → assumptions → plan → risk): 4–6 thoughts.
- Refactor safety check (blast radius → test coverage → order of changes): 3–5 thoughts.

## Bug diagnosis template

```
Plan: 5 thoughts. Subject: <reproduce and fix <symptom>>.

### Thought 1
Reproduce: exact command or input that triggers the bug.

### Thought 2
Isolate: narrow to the smallest failing case; identify the bad assumption.

### Thought 3
Trace: follow the execution path from the symptom back to the cause.
Cite path:line for each relevant call.

### Thought 4
Fix options: list 1–3 candidate fixes with their tradeoffs.

### Thought 5
Verification: does the chosen fix address the root cause? What regression
test would catch this?

### Final
Chosen fix and rationale. Remaining unknowns.
```

## Architecture decision template

```
Plan: 6 thoughts. Subject: choose <component> approach for <context>.

### Thought 1
Constraints: list hard constraints (latency, ops cost, team expertise, existing deps).

### Thought 2
Option A: describe, with strengths and failure modes.

### Thought 3
Option B: describe, with strengths and failure modes.

### Branch A from 3
(If a third option warrants exploration.) Describe option C.

### Thought 4
Compare A vs B on the constraints from Thought 1.

### Thought 5
ASSUMPTION: <any unverified constraint that changes the verdict if wrong>.

### Thought 6 (revises 5 if assumption was checked)
Verification: does the conclusion follow from cited constraints, or only
from the assumption? Is the tradeoff explicit?

### Final
Recommended option and the one or two constraints that decided it.
```

## Revision discipline

A revision must name what it corrects:

```
### Thought N (revises M)
<corrected version>
Reason: Thought M assumed X; actual behavior is Y (cite evidence).
```

Do not use `(revises M)` to extend an idea. Extension = new thought number
with no revision tag. Revision = old conclusion was wrong.

## Branch resolution

Every branch must close before `### Final`. Closing options:

- Picked: "Branch A selected; Branch B rejected because X."
- Rejected inline: add `(rejected: <one-line reason>)` to the branch's last thought.
- Deferred: "Branch A deferred; outside current scope; tracked as follow-up."

A branch that opens and never closes leaves the reader unable to tell whether
you forgot or are still deciding.

## Verification gate checklist

Run this before `### Final`:

1. Conclusion follows from cited evidence, not only from assumptions.
2. Every `ASSUMPTION:` tag either has been checked and updated or is
   explicitly accepted as a remaining risk in Final.
3. All open branches are resolved.
4. If the user asked for a recommendation, one is named — not hedged with
   "it depends" without saying what it depends on.

If any item fails, add one more Thought addressing it. Then write Final.
