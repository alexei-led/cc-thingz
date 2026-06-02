# Implementation modes (Step 3)

Ask multi-choice: "How should we implement this task?"

- Solo engineer — single agent implements
- Implementation pair — engineer + test specialist work as a team (tests written in parallel)
- Team research first — explore with team before implementing

## Solo engineer (default)

Detect language from task / epic, then delegate to the `engineer` role (it self-detects language). Prompt:

```
Implement: <task description>
Plan: <plan>
Apply the changes and run the project build/test/lint verification.
```

The engineer applies and verifies (it is the only mutator role). Step 4 re-runs verification; Step 7 shows the scoped diff for review before continuing.

## Implementation pair

Spawn a two-member team:

- Primary: `engineer` role — applies implementation code.
- Secondary: test specialist (the `reviewer` role with the improving-tests skill) — proposes tests in parallel (read-only; emits the Proposed Changes contract), identifies coverage gaps.

Have them coordinate: engineer drafts implementation, the tests reviewer proposes tests, both critique each other, converge. The engineer applies the converged implementation and the reviewer's test proposals, then verifies. Step 7 shows the scoped diff for review.

## Team research first

Spawn a research team — exploration agent, language engineer, language tests reviewer — to share findings and converge on approach. Then proceed with solo or pair.
