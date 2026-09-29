# Grill Protocol

Interview the user about each decision branch of a bounded plan, trade-off, or
assumption set until the branch is resolved or explicitly deferred.

Order branches by risk, not by category, and skip what the plan already answers.
For a concrete plan, open on its riskiest step or assumption — an irreversible
action, a missing rollback, an all-at-once cutover, concurrent writes during a
migration — before scope, goals, or environment; ask those only if the plan
leaves them unclear.

Ask exactly one question per turn; its options are the only content in that turn.
Give:

- Question: the decision to resolve.
- My take: your recommended answer and why.
- Options: 2-4 choices, including defer when legitimate.
- Why it matters: the cost of choosing wrong.

When code contradicts an assumption, show the path and resolve the discrepancy
before continuing. If the user deflects, repeat the open branch or offer to defer
it. Defer new topics that come up mid-branch and finish the current one.

Finish with:

```text
GRILL COMPLETE
Locked:
- <decision>: <outcome>
Deferred:
- <item>: <reason>
Constraints surfaced:
- <constraint>
```
