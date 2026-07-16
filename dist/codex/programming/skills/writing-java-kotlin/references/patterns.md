# Java and Kotlin patterns

Use when changing JVM package layout, services, framework boundaries, persistence,
or build structure.

## Layout and build seams

- Follow the existing source-set layout: `src/main/java`, `src/main/kotlin`, `src/test/java`, `src/test/kotlin`, generated sources, and module boundaries.
- Prefer one clear module owner for a domain area. Do not add cross-module imports that bypass public APIs.
- In Gradle multi-project builds, keep dependencies flowing from app/adapters toward domain modules only when that is the intended architecture.
- Put shared build policy in convention plugins, version catalogs, parent POMs, or `Directory`-style build files already used by the repo. Do not copy plugin blocks everywhere.

## Services and frameworks

- Keep controllers, routes, message listeners, jobs, and CLI entrypoints thin.
- Put request mapping, auth, serialization, transaction, and HTTP status policy at the framework edge.
- Keep domain services framework-light. Inject ports or concrete collaborators that match project style.
- Avoid static global state for configuration, clocks, clients, executors, coroutine scopes, or mutable caches.
- Prefer constructor injection where the framework supports it.

## Persistence and serialization

- Do not leak JPA entities, Exposed records, generated API models, or ORM sessions through stable domain interfaces unless the project already does.
- Keep transaction boundaries explicit and close to use cases.
- Avoid lazy-loading surprises across service/API boundaries.
- Validate serialized input before constructing domain values.

## Java/Kotlin interop

- For Java-called Kotlin APIs, use explicit nullability, stable names, and `@JvmStatic` / `@JvmOverloads` only when they improve actual call sites.
- For Kotlin-called Java APIs, handle platform types at the boundary and avoid spreading `T!` assumptions.
- Avoid Kotlin extension functions that hide expensive I/O or mutate distant state.
- Keep annotations consistent: nullability, validation, serialization, transactional, and DI annotations should match the framework stack.

## Dependencies

- Prefer BOMs, version catalogs, or existing dependency-management blocks.
- Keep test fixtures and test utilities in test source sets, not production modules.
- Avoid adding reflection-heavy or bytecode-weaving tools unless the project already uses them or the requirement needs them.
