# Grill Protocol

Interview the user about each decision branch of a bounded plan, trade-off, or
assumption set until the branch is resolved or explicitly deferred. Walk the tree
depth-first, in this order:

1. Scope: problem framing, goals, explicit non-goals.
2. Decisions: key design choices, dependencies, constraints.
3. Edge cases: failure modes, rollback, scale limits.

For each branch, give:

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
