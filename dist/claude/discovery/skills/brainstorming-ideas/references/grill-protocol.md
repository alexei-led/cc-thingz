# Grill Protocol

Use this for a bounded plan, trade-off, or assumption set. Interview the user
about key decision branches until each branch is resolved or explicitly deferred.
Walk the decision tree depth-first.

## Question discipline

- Ask one question at a time.
- Give your recommendation before asking the user.
- Use the runtime's interactive question tool when available.
- Use single-select when branches are mutually exclusive.
- Use multi-select when several risks, constraints, or open questions can apply.
- Allow free text or Other for custom answers.
- Do not ask users to type numeric choices unless no interactive tool exists.

If code can answer a question, read it first. Ask only what code and docs do not
settle. Cite paths when code contradicts or shapes the answer.

## Phase order

1. Scope: problem framing, goals, explicit non-goals.
2. Decisions: key design choices, dependencies, constraints.
3. Edge cases: failure modes, rollback, scale limits.

## Per-question content

For each branch:

- Question: the decision to resolve.
- My take: your recommended answer and why.
- Options: 2-4 choices, including defer when legitimate and Other when needed.
- Why it matters: the consequence of choosing wrong.

Use the interactive question tool to ask the question. If no tool is available,
fall back to concise labeled options.

## Final summary

```text
GRILL COMPLETE
Locked:
- <decision>: <outcome>
Deferred:
- <item>: <reason>
Constraints surfaced:
- <constraint>
```

## Failure handling

- Plan too vague: ask for the plan first; do not invent decisions.
- User deflects: repeat the unresolved branch or ask whether to defer it.
- Code contradicts an assumption: surface the path-backed discrepancy and resolve it before continuing.
- Scope creep: defer the new topic; finish the current branch.
