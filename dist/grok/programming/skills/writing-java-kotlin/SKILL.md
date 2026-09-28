---
{"description":"Idiomatic modern Java and Kotlin JVM development. Use when writing `.java`, `.kt`, or `.kts` code; changing Gradle or Maven builds; or working on Spring, Micronaut, Quarkus, Ktor, Android JVM modules, JUnit, Mockito, Kotest, ktlint, detekt, or JVM CLI/services. Emphasizes JDK toolchains, null-safety, fast focused Gradle/Maven feedback, deterministic formatting, and minimal dependencies. NOT for JavaScript/TypeScript, C#/.NET, Python, shell scripts, or infra-only work.","name":"writing-java-kotlin"}
---

# Java and Kotlin Development

## Build Baseline

- Read the wrapper properties, `settings.gradle*`, `build.gradle*` or `pom.xml`, `gradle.properties`, and CI before using version-specific Java, Kotlin, or plugin behavior.
- Use `./gradlew` and `./mvnw` when the repo has them, not global `gradle` or `mvn`.
- The compile target is the configured Java toolchain and Kotlin `jvmToolchain`, not the shell's `JAVA_HOME`.
- Use a Java or Kotlin language feature only when the configured toolchain, language version, and CI target support it. Preview features need explicit approval and a visible compiler flag.
- Shared build policy lives in convention plugins, version catalogs, BOMs, or parent POMs; do not copy plugin or version blocks into modules.

## Defaults

- JDK, Kotlin stdlib, and existing dependencies first. Avoid new reflection-heavy or bytecode-weaving tools.
- Kotlin: structured coroutines only, never `GlobalScope`; pass scopes or suspend through the chain.
- Kotlin: handle Java platform types at the boundary instead of not-null assertions (`!!`).
- Java: virtual threads for blocking I/O only, not CPU-bound work. Never swallow `InterruptedException`; restore the flag or propagate.
- Keep blocking calls off event-loop and coroutine dispatcher threads unless the framework allows it.
- Constructor injection. No static state for config, clocks, clients, executors, or scopes.
- Do not leak JPA entities, ORM sessions, or generated API models through domain interfaces. Keep transactions explicit and near the use case; watch lazy loading across API boundaries.
- Kotlin APIs called from Java: explicit nullability, and `@JvmStatic`/`@JvmOverloads` only where call sites benefit.

## CLIs

Use the existing stack (picocli, Clikt, plain `main`). Keep `main` thin, test through the command entrypoint with captured stdout, stderr, and exit code, and close executors, pools, and dispatchers the process owns.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when Gradle/Maven test runs are slow.
- [linting.md](references/linting.md): read when changing formatters, ktlint, detekt, Spotless, or static analysis.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
