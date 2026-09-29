---
{"agent":"engineer","allowed-tools":["Read","Bash","Grep","Glob","Edit","Write","LS"],"context":"fork","description":"Idiomatic modern Java and Kotlin JVM development. Use when writing `.java`, `.kt`, or `.kts` code; changing Gradle or Maven builds; or working on Spring, Micronaut, Quarkus, Ktor, Android JVM modules, JUnit, Mockito, Kotest, ktlint, detekt, or JVM CLI/services. Emphasizes JDK toolchains, null-safety, fast focused Gradle/Maven feedback, deterministic formatting, and minimal dependencies. NOT for JavaScript/TypeScript, C#/.NET, Python, shell scripts, or infra-only work.","name":"writing-java-kotlin","user-invocable":false}
---

# Java and Kotlin Development

## Build baseline

- Read the wrapper properties, `settings.gradle*`/`build.gradle*` or `pom.xml`, and CI before relying on version-specific behavior.
- Use `./gradlew`/`./mvnw`, never a global `gradle`/`mvn`; scope tests to the changed module (see testing.md).
- The compile target is the configured Java toolchain and Kotlin `jvmToolchain`, never the shell's `JAVA_HOME`.
- Toolchain, plugin, and dependency versions live in convention plugins, version catalogs, BOMs, or parent POMs, set once there — including a toolchain bump for a new language feature, which needs approval like a preview feature, not a single-module fix.
- A preview feature needs approval before writing code that enables it — even when the request names the feature directly, that isn't approval — a non-preview fallback, and, once approved, a visible `--enable-preview` flag in the build's compile and run/test tasks, not a local flag. Previews can be withdrawn between JDKs: string templates were pulled after JDK 22, never reinstated.
- Wire coverage, mutation, or other heavy analysis as its own task or under `check`, never `dependsOn`/`finalizedBy` on `test` — a finalizer still runs on every plain `test`. Keep it off that default loop even when adding it is the task; use a separate command or CI step.

## Defaults

- Kotlin: structured concurrency only — no `GlobalScope`; pass a `coroutineScope` or an injected scope through the call chain. Test coroutine code with `kotlinx-coroutines-test`'s `runTest`, not `runBlocking` or real delays.
- Kotlin: resolve nullable Java platform types at the boundary instead of asserting past them with `!!`.
- Java: say outright when virtual threads help (blocking I/O) versus don't (CPU-bound work); size CPU-bound work to a bounded pool near the processor count or a parallel stream. Never swallow `InterruptedException` — restore the flag or propagate it — and close any executor you own instead of holding it in static state.
- Don't return JPA entities or their ORM sessions from an API; map to a DTO inside an explicit transaction near the use case, loading what it needs (fetch join or entity graph) instead of enabling `spring.jpa.open-in-view`.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when Gradle/Maven test runs are slow.
- [linting.md](references/linting.md): read when changing formatters, ktlint, detekt, Spotless, or static analysis.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
