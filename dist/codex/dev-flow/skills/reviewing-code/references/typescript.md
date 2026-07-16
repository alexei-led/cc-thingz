# TypeScript Review Reference

Host skill owns scope, severity, scoring, and output. This file adds TypeScript-specific evidence gathering and checks.

## Tool-enabled review

Run configured project tools only when the active role can execute commands. Prefer project commands and package manager conventions when present.

Useful TypeScript gates:

```bash
bunx tsc --noEmit
bun test
npm audit --omit=dev
```

Use the project's package manager instead of forcing Bun or npm. Treat tool output as evidence, then map it through the severity rubric. If a tool is missing or not configured, report the gap and continue source review. Do not install tools.

## Read-only review

When commands are unavailable, use supplied diff, file reads, and caller-supplied output. Follow direct callers for changed exported functions, route handlers, components, schemas, API clients, and persistence code.

## Focus checks

Correctness:

- Runtime data trusted only by TypeScript types instead of validation at the boundary.
- Missing null or undefined guards before dereference.
- Non-exhaustive discriminated union handling.
- Floating promises, missing `await`, or lost rejection handling.
- API, schema, or component prop contract changed without updating callers.

Security:

- SQL, NoSQL, command, template, or HTML injection from untrusted input.
- Missing auth or ownership check at route, resolver, server action, or service boundary.
- Prototype pollution from merging untrusted objects.
- XSS through raw HTML sinks or unsafe markdown/rendering paths.
- Weak crypto, insecure cookies, token leakage, or secrets in client bundles/logs.
- CORS or security-header changes that expose credentials or debug details.

Reliability:

- Missing timeout or abort handling for external calls.
- Resource or subscription cleanup missing in server streams, workers, or React effects.
- Retry loops without cap, backoff, or idempotency check.
- Shared mutable state in request handlers or tests.

Performance:

- Blocking sync I/O in request or render paths.
- N+1 database/API calls or sequential awaits that should be batched.
- Unbounded concurrency, memory growth, or cache retention.
- Expensive React renders from unstable dependencies or unnecessary state, only when user-visible or realistic.

Tests:

- Changed behavior without tests for success, failure, and boundary cases.
- Bug fixes without a regression test at the route, service, or component contract.
- Tests that assert implementation details instead of observable behavior.

## Boundary validation

Do not flag all external data usage just because no schema library is visible. Flag concrete cases where untrusted input reaches sensitive behavior without a visible guard.

External input includes HTTP bodies, params, query strings, headers, cookies, environment variables, storage, messages, webhooks, database rows crossing trust boundaries, and third-party API responses.

## Framework checks

Apply only when the framework is present in scope:

- React: hooks dependencies, stale closures, controlled/uncontrolled form state, cleanup in effects, accessible interactive elements.
- Node servers: request validation, auth, error exposure, timeouts, streaming cleanup.
- Next or server actions: server/client boundary leaks, cache invalidation, auth at server entry points.

## Failure handling

- Typecheck, test, or audit failure in reviewed scope: map severity by impact; blocking failures are Critical.
- Ambiguous security risk: use Needs review and name the missing trust boundary, framework behavior, or configuration.
- Audit output without exploitability in shipped dependencies: do not overstate; report severity by reachability and package scope.
- LSP or graph unavailable: note reduced cross-file coverage only if it affects the finding.
