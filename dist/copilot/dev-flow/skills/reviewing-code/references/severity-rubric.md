# Review Severity Rubric

Use this rubric for every code-review finding. A finding needs evidence, impact,
and a concrete fix. If one is missing, downgrade it or move it to Needs review.

## Finding fields

Each finding includes:

- Severity: Critical, Warning, Suggestion, or Needs review.
- Category: security, correctness, tests, reliability, performance, maintainability, or docs.
- Confidence: high, medium, or low.
- Evidence: `file:line` or quoted tool output.
- Scenario: how the bug, exploit, missed behavior, or future failure happens.
- Fix: the smallest concrete change that resolves it.

## Dimension scope

Security:

- Auth, authorization, injection, unsafe deserialization, secrets, crypto, SSRF, XSS, CSRF, path traversal, data exposure.

Correctness:

- Logic errors, edge cases, null or empty handling, contract mismatches, broken callers, unchecked errors, migrations, API compatibility.

Tests:

- Missing regression tests, uncovered changed behavior, weak assertions, over-mocking, missing error or boundary cases.

Reliability:

- Resource leaks, retries, timeouts, cancellation, concurrency, races, idempotency, cleanup, observability for failures.

Performance:

- Realistic hot paths, unbounded work, N+1 queries, blocking I/O, memory growth, avoidable cost.

Maintainability:

- Dead code, confusing indirection, shallow wrappers, mixed responsibilities, brittle coupling, unclear invariants.

Simplicity (over-engineering):

- Reinvented stdlib or native behavior, single-implementation abstractions, factories with one product, speculative flexibility, dependencies a few lines would replace, dead flags or config.

Docs:

- Public API docs, migration notes, user-facing behavior, accessibility text, and operator docs affected by the change.

## Severity anchors

Critical:

- Exploitable security issue.
- Data loss, data corruption, or privacy leak.
- Crash, deadlock, race, or resource leak in a normal or high-risk path.
- Broken core behavior, public API contract, migration, auth, billing, or permission check.
- Build, typecheck, lint, or test failure in the reviewed scope.

Warning:

- Likely correctness bug in an edge or realistic path.
- Missing validation, authorization, timeout, error handling, or cleanup at a concrete boundary.
- Meaningful test gap for changed business behavior, bug fix, or risky branch.
- Performance problem that can affect realistic input size, hot paths, or cost.
- Maintainability issue likely to cause future defects, not just preference.

Suggestion:

- Clear improvement to readability, local structure, docs, or test clarity.
- Non-blocking cleanup with a concrete payoff.
- Minor performance or maintainability improvement with low risk.

Needs review:

- Plausible risk where required context is missing.
- Tooling, runtime, config, server-side code, or generated context is unavailable.
- External dependency or deployment behavior must be checked before asserting a defect.

Do not count Needs review as a confirmed finding. Use it to preserve uncertainty without inflating defects.

## Confidence anchors

High:

- Evidence directly proves the issue.
- Failure scenario follows from the shown code or tool output.
- Fix is clear and local.

Medium:

- Evidence is strong, but one assumption depends on nearby code, configuration, or runtime behavior.
- The scenario is realistic but not directly reproduced.

Low:

- Evidence suggests risk, but missing context prevents a confirmed finding.
- Prefer Needs review unless the risk is severe and the missing context is explicit.

## Decision rules

- No evidence, no finding.
- No concrete scenario, at most Suggestion.
- Missing context, use Needs review instead of hedged language.
- Style, naming, or formatting is only a finding when it harms correctness, maintainability, docs, or tests materially.
- Tool findings map to the severity above; do not treat every tool warning as Critical.
- Security findings need an attack path or sensitive asset. If context is missing, use Needs review.
- Test findings must name the missing behavior or branch, not just say coverage is low.

## Review score

Only score when the user asks for a score or when the active review mode requires one.
Start at 10 and apply caps before deductions.

Caps:

- Any confirmed Critical: maximum 5.
- Two or more confirmed Critical findings: maximum 4.
- Exploitable security, data loss, data corruption, or privacy leak: maximum 3.
- Build, typecheck, lint, or test failure in reviewed scope: maximum 6.
- Missing tests for risky changed behavior: maximum 7.
- Partial review because scope, diff, tools, or context is missing: maximum 8.
- Mostly low-confidence findings: maximum 7.

Deductions after caps:

- Warning: subtract 1, up to 3 total.
- Suggestion: subtract 0.25, up to 1 total.
- Needs review: no deduction unless it blocks review completeness; then use the partial-review cap.

Calibration anchors:

- 10: complete review, no confirmed findings, relevant tests present or unchanged risk.
- 8: no bugs; only minor maintainability, docs, or test clarity suggestions.
- 6: one real Warning, or missing tests for meaningful changed logic.
- 4: one Critical in correctness, security, reliability, or build/test health.
- 2: exploitable security issue, data loss, or broken core path with high confidence.

If two scores seem plausible, choose the lower score only when the evidence matches a cap. Otherwise choose the midpoint and mark confidence medium.
