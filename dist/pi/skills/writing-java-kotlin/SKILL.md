---
{"description":"Idiomatic modern Java and Kotlin JVM development. Use when writing `.java`, `.kt`, or `.kts` code; changing Gradle or Maven builds; or working on Spring, Micronaut, Quarkus, Ktor, Android JVM modules, JUnit, Mockito, Kotest, ktlint, detekt, or JVM CLI/services. Emphasizes JDK toolchains, null-safety, fast focused Gradle/Maven feedback, deterministic formatting, and minimal dependencies. NOT for JavaScript/TypeScript, C#/.NET, Python, shell scripts, or infra-only work.","name":"writing-java-kotlin"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly, including extension toolsets such as Task*, Monitor*, and Loop*. -->
<!-- When available, track work with Task* (`todo` is the fallback), run long or background commands with MonitorCreate, and schedule follow-up with LoopCreate instead of sleep/poll loops. -->


# Java and Kotlin Development

## Build baseline

- Read the wrapper properties, `settings.gradle*`/`build.gradle*` or `pom.xml`, and CI before relying on version-specific Java, Kotlin, or plugin behavior.
- Use `./gradlew`/`./mvnw` when the repo has them, never a global `gradle`/`mvn`. Scope the test command to the changed module, e.g. `./gradlew :billing:test --tests '*FooTest'` or `./mvnw -q -pl module -Dtest=FooTest test`.
- The compile target is the configured Java toolchain and Kotlin `jvmToolchain`, never the shell's `JAVA_HOME`.
- Toolchain, plugin, and dependency versions live in convention plugins, version catalogs, BOMs, or parent POMs — set once there, not copied into one module. Raising the toolchain to use a newer language feature needs approval too, the same as a preview feature; don't bump it in a single module to unblock one change.
- A preview feature needs more than toolchain and CI support: stop and ask for explicit approval before writing code that enables it — even when the request names the feature directly, that is not approval — name a non-preview fallback, and, if approved, add `--enable-preview` to the build's compile and run/test tasks so it is a visible, committed setting rather than a local flag. Previews can be withdrawn between JDKs — string templates were pulled after JDK 22 and never reinstated.
- Add coverage, mutation, or other heavy analysis as its own task (or under `check`) with no edge back to `test` — not `dependsOn`, and not `finalizedBy` either, since a finalizer still runs on every plain `test` invocation. Keep it off that default loop even when adding it is the task at hand; run it as its own command or CI step instead.

## Defaults

- JDK/Kotlin stdlib and existing dependencies first; avoid new reflection-heavy or bytecode-weaving tools.
- Kotlin: structured concurrency only — no `GlobalScope`; pass a `coroutineScope` or an injected scope through the call chain. Test coroutine code with `kotlinx-coroutines-test`'s `runTest`, not `runBlocking` or real delays.
- Kotlin: resolve nullable Java platform types at the boundary instead of asserting past them with `!!`.
- Java: when reviewing or writing concurrency, say outright that virtual threads help blocking I/O and do not speed up CPU-bound work; size CPU-bound work to a bounded pool near the available processor count or a parallel stream instead. Never swallow `InterruptedException`: restore the flag or propagate it, and close any executor you own instead of holding it in static state.
- Constructor injection; no static state for config, clocks, clients, or scopes.
- Don't return JPA entities or their ORM sessions from an API; map to a DTO inside an explicit transaction near the use case. Load what that transaction needs (fetch join or entity graph) instead of enabling `spring.jpa.open-in-view`.
- Kotlin called from Java: explicit nullability, `@JvmStatic`/`@JvmOverloads` only where a call site benefits.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when Gradle/Maven test runs are slow.
- [linting.md](references/linting.md): read when changing formatters, ktlint, detekt, Spotless, or static analysis.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
