---
description: Idiomatic modern Java and Kotlin JVM development. Use when writing `.java`,
  `.kt`, or `.kts` code; changing Gradle or Maven builds; or working on Spring, Micronaut,
  Quarkus, Ktor, Android JVM modules, JUnit, Mockito, Kotest, ktlint, detekt, or JVM
  CLI/services. Emphasizes JDK toolchains, null-safety, fast focused Gradle/Maven
  feedback, deterministic formatting, and minimal dependencies. NOT for JavaScript/TypeScript,
  C#/.NET, Python, shell scripts, or infra-only work.
name: writing-java-kotlin
---

# Java and Kotlin Development

## Build baseline

- Read the wrapper properties, `settings.gradle*`/`build.gradle*`/`gradle.properties` or `pom.xml`, and CI before relying on version-specific behavior.
- Use `./gradlew`/`./mvnw` when the repo has them; scope tests to the changed module (see testing.md).
- The compile target is the declared Java toolchain and Kotlin `jvmToolchain`, not the shell's `JAVA_HOME`; without one, the running JDK compiles.
- Toolchain, plugin, and dependency versions live in convention plugins, version catalogs, BOMs, or parent POMs, set once there. Raising the Java or Kotlin toolchain is a project-wide decision: ask, and change it in shared build config, not one module.
- A request to use a preview feature is not approval to enable it: ask first, name a non-preview fallback, and, once approved, add `--enable-preview` to the build's compile and run/test tasks, not a local flag. Previews can be withdrawn between JDKs: string templates were withdrawn in JDK 23.
- Wire coverage, mutation, or other heavy analysis as its own task or under `check`; never make `test` depend on or be finalized by the report, which would still run it on every plain `test`. Use a separate command or CI step, even when adding it is the task.

## Defaults

- Kotlin: structured concurrency only — no `GlobalScope`; pass a `coroutineScope` or an injected scope through the call chain. Test coroutine code with `kotlinx-coroutines-test`'s `runTest`, not `runBlocking` or real delays. Keep blocking calls off event-loop and coroutine dispatcher threads unless the framework allows it.
- Kotlin: resolve nullable Java platform types at the boundary instead of asserting past them with `!!`.
- Java: say outright when virtual threads help (blocking I/O) versus don't (CPU-bound work); size CPU-bound work to a bounded pool near the processor count or a parallel stream. Never swallow `InterruptedException` — restore the flag or propagate it. No static state for config, clocks, clients, executors, or scopes.
- Don't leak JPA entities, ORM sessions, or generated API models through domain interfaces; map to a DTO while the transaction is open, loading what it needs (fetch join or entity graph) instead of keeping the session open via `spring.jpa.open-in-view`.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when Gradle/Maven test runs are slow.
- [linting.md](references/linting.md): read when changing formatters, ktlint, detekt, Spotless, or static analysis.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
