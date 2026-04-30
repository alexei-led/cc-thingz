---
description: Implementation process discipline for all languages — surface assumptions,
  define verifiable success criteria, and ground work in project domain docs. Use
  when implementing features, writing functions/classes/modules, or adding code. Complements
  language-specific skills and includes test-first guidance when implementation is
  explicitly TDD.
name: coding
---

<!-- Platform guidance for non-Claude models (Codex CLI, Gemini CLI) -->
<!-- Persistence: Keep going until the task is fully resolved. Do not stop at the first obstacle. -->
<!-- Tool use: Use available tools to verify — do not guess at file contents, paths, or command output. -->
<!-- Planning: Reflect between steps. Decompose complex problems into logical sub-steps before acting. -->
<!-- Reliability: Assess risk before irreversible actions. Ask for clarification on ambiguity. -->
<!-- Completeness: Generate complete responses without truncating. Review your output against the original constraints. -->

# Coding Process Discipline

## Before Writing Code

State assumptions. Do not pick an interpretation silently.

- Ambiguous request → name the interpretations and ask one clarifying question.
- Simpler approach exists → say so before coding.
- Existing project glossary or ADRs exist → read them before naming concepts or changing architecture:
  - `CONTEXT.md`
  - `CONTEXT-MAP.md`
  - `docs/adr/`
  - nearest `*/CONTEXT.md` or `*/docs/adr/`

## Define Success Criteria First

Transform the task into verifiable goals.

| Vague            | Verifiable                                          |
| ---------------- | --------------------------------------------------- |
| "Add validation" | Write invalid-input tests, then make them pass      |
| "Fix the bug"    | Reproduce with a test or script, then make it pass  |
| "Refactor X"     | Tests pass before and after, diff stays minimal     |

For multi-step work, state a brief plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

## Test-First Mode

Use this when the user asks for TDD, test-first, or red-green-refactor.

- Test behavior through public interfaces. Do not test private helpers.
- Write one failing test for one behavior.
- Add only enough code to pass that test.
- Repeat one vertical slice at a time. Do not write all tests first.
- Refactor only when green.
- Mock only system boundaries: network, time, randomness, filesystem, external services.

Cycle:

```text
RED: one behavior test fails
GREEN: minimal implementation passes
REFACTOR: simplify without changing behavior
```

## During Implementation

Every changed line must trace to the request.

When done, check the diff:

- Extra feature? Remove it.
- Speculative abstraction? Delete it.
- Name conflicts with `CONTEXT.md` vocabulary? Rename to match the domain language.
- Decision is hard to reverse, surprising, and a real trade-off? Offer an ADR.
