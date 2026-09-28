# TypeScript Review Focus

Use writing-typescript for toolchain commands and the project's package manager.

- Runtime data trusted by type alone. Flag concrete untrusted input (bodies, params, headers, env, storage, webhooks, third-party responses) reaching sensitive behavior without a guard; do not flag every boundary for lacking a schema library.
- Floating promises, missing `await`, lost rejections; non-exhaustive discriminated unions.
- Prototype pollution from merging untrusted objects; raw HTML or markdown sinks; secrets in client bundles.
- Auth or ownership missing at routes, resolvers, and server actions; CORS or header changes exposing credentials.
- Sequential awaits that should batch; sync I/O in request or render paths; unbounded caches or concurrency.
- React: effect dependencies, stale closures, missing effect cleanup. Next/server actions: server/client boundary leaks, cache invalidation.
- Audit output: rate by reachability in shipped dependencies, not raw advisory severity.
