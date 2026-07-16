# Java and Kotlin principles

Read before writing, changing, or reviewing Java/Kotlin JVM code.

## Project baseline

- Start from `settings.gradle*`, `build.gradle*`, `pom.xml`, `gradle.properties`, wrapper files, CI, and nearby code.
- Follow the configured JDK toolchain, Kotlin language/API version, compiler flags, formatter, nullability annotations, and static-analysis rules.
- Prefer the JDK, Kotlin stdlib, and existing dependencies. Add Maven/Gradle dependencies only for a concrete requirement.
- Keep domain logic separate from framework controllers/routes, DI modules, persistence, serialization, logging, and process wiring.
- Use Java and Kotlin together deliberately. Do not create awkward Java APIs for Kotlin callers or vice versa without checking call sites.

## Types and nullability

- Model optional values honestly: Java `Optional` at return boundaries when project style uses it; Kotlin nullable types when absence is real.
- Do not silence nullability with `!!`, platform-type assumptions, blanket suppressions, or broad `@SuppressWarnings`.
- Prefer immutable values: Java records or final fields; Kotlin `val`, data classes, and read-only collection interfaces.
- Keep public APIs stable and explicit. Avoid exposing mutable collections, framework request/response types, or persistence entities across stable seams.
- Validate JSON, HTTP input, env/config, and message payloads before typed domain use.

## Concurrency and effects

- Java: use virtual threads only when the project targets Java 21+ and the workload is blocking I/O. Do not use them to hide CPU-bound work or shared-state races.
- Kotlin: use structured coroutines. Avoid `GlobalScope`; pass scopes or suspend through the call chain.
- Always propagate cancellation and timeouts across HTTP, DB, queue, coroutine, and process boundaries.
- Close resources with try-with-resources or Kotlin `use`.
- Keep blocking calls out of event-loop or dispatcher threads unless the framework explicitly permits it.

## Errors and boundaries

- Keep validation, HTTP status mapping, CLI exit codes, retries, and transaction policy at the edge.
- Throw specific exceptions with useful context when exceptions are the local convention.
- Prefer sealed results or typed domain errors only when callers need explicit branching and the project already uses that style.
- Do not swallow `InterruptedException`; restore interruption or propagate cancellation.

## Verification

- Run focused Gradle/Maven tests and format/lint before claiming success.
- Fix compiler, nullability, detekt, ktlint, Error Prone, Checkstyle, PMD, or SpotBugs findings at the cause instead of weakening rules.
