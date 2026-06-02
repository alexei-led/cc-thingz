# Grill Protocol

Interview the user about key decision branches until each is resolved or explicitly deferred. Walk the decision tree depth-first. For each question, give your recommendation before waiting for theirs.

Ask one question at a time.

If a question can be answered by reading the codebase, read it first. Ask only what the code does not settle. Cite paths when code contradicts or shapes the answer.

## Phase order

1. Scope: problem framing, goals, explicit non-goals.
2. Decisions: key design choices, dependencies, constraints.
3. Edge cases: failure modes, rollback, scale limits.

## Per-question format

```
Q{n}: [question]
→ My take: [your recommendation and why]
```

## Final summary

When all branches are resolved or explicitly deferred, emit:

```
GRILL COMPLETE
==============
Locked:
- [decision]: [outcome]

Deferred:
- [item]: [reason]

Constraints surfaced:
- [constraint]
```

## Failure handling

- Plan too vague: ask for the plan first; do not invent decisions.
- User deflects: repeat the question until answered or explicitly deferred.
- Code contradicts an assumption: surface the path-backed discrepancy and resolve it before continuing.
- Scope creep: defer the new topic; finish the current branch.
