# Review Severity Rubric

Every finding needs evidence, impact, and a concrete fix. If one is missing,
downgrade it or move it to Needs review.

## Finding fields

- Severity: Critical, Warning, Suggestion, or Needs review.
- Category: one of the dimensions below.
- Confidence: high, medium, or low.
- Evidence: `file:line` or quoted tool output.
- Scenario: how the bug, exploit, missed behavior, or future failure happens.
- Fix: the smallest concrete change that resolves it.

## Dimensions

- **Security**: auth, authorization, injection, unsafe deserialization, secrets, crypto, SSRF, XSS, CSRF, path traversal, data exposure.
- **Correctness**: logic errors, edge cases, null or empty handling, contract mismatches, broken callers, unchecked errors, migrations, API compatibility.
- **Tests**: missing regression tests, uncovered changed behavior, weak assertions, over-mocking, missing error or boundary cases.
- **Reliability**: resource leaks, retries, timeouts, cancellation, races, idempotency, cleanup, failure observability.
- **Performance**: realistic hot paths, unbounded work, N+1 queries, blocking I/O, memory growth, avoidable cost.
- **Maintainability**: dead code, confusing indirection, shallow wrappers, mixed responsibilities, brittle coupling, unclear invariants.
- **Simplicity**: reinvented stdlib or native behavior, single-implementation abstractions, speculative flexibility, dependencies a few lines would replace, dead flags or config.
- **Docs**: public API docs, migration notes, user-facing behavior, accessibility text, operator docs affected by the change.

## Severity

Critical:

- Exploitable security issue; data loss, corruption, or privacy leak.
- Crash, deadlock, race, or resource leak in a normal or high-risk path.
- Broken core behavior, public API contract, migration, auth, billing, or permission check.
- Build, typecheck, lint, or test failure in the reviewed scope.

Warning:

- Likely correctness bug in an edge or realistic path.
- Missing validation, authorization, timeout, error handling, or cleanup at a concrete boundary.
- Meaningful test gap for changed business behavior, a bug fix, or a risky branch.
- Performance problem at realistic input size, hot path, or cost.
- Maintainability issue likely to cause defects, not just preference.

Suggestion:

- Non-blocking improvement to readability, structure, docs, tests, or performance with a concrete payoff.

Needs review:

- Plausible risk where required context (tooling, runtime, config, server-side or generated code, deployment behavior) is unavailable.
- Not a confirmed finding; it preserves uncertainty without inflating defects.

## Confidence

- **High**: evidence directly proves the issue; the fix is clear and local.
- **Medium**: evidence is strong, but one assumption depends on nearby code, config, or runtime behavior.
- **Low**: missing context prevents confirmation. Prefer Needs review unless the risk is severe and the gap is explicit.

## Decision rules

- No evidence, no finding. No concrete scenario, at most Suggestion.
- Missing context goes to Needs review, not hedged language.
- Style, naming, or formatting is a finding only when it materially harms correctness, maintainability, docs, or tests.
- Map tool warnings by impact; not every warning is Critical.
- Security findings need an attack path or sensitive asset.
- Test findings name the missing behavior or branch, not "coverage is low".

## Score

Score only when asked. Start at 10, apply caps, then deductions. State score
confidence and, for partial coverage, the cap reason. Use one decimal only when
arithmetic needs it.

Caps:

- Any confirmed Critical: max 5. Two or more: max 4.
- Exploitable security, data loss, corruption, or privacy leak: max 3.
- Build, typecheck, lint, or test failure in scope: max 6.
- Missing tests for risky changed behavior: max 7.
- Mostly low-confidence findings: max 7.
- Partial review (scope, diff, tools, or context missing): max 8.

Deductions: Warning −1 (max −3); Suggestion −0.25 (max −1); Needs review 0
unless it blocks completeness, then use the partial-review cap.

Anchors:

- 10: complete review, no confirmed findings, relevant tests present.
- 8: only minor maintainability, docs, or test-clarity suggestions.
- 6: one real Warning, or missing tests for meaningful changed logic.
- 4: one Critical in correctness, security, reliability, or build/test health.
- 2: high-confidence exploitable security issue, data loss, or broken core path.

Between two plausible scores, take the lower only when evidence matches a cap;
otherwise take the midpoint with medium confidence.
