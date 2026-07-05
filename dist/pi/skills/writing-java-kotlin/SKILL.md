---
description: Idiomatic modern Java and Kotlin JVM development. Use when writing `.java`,
  `.kt`, or `.kts` code; changing Gradle or Maven builds; or working on Spring, Micronaut,
  Quarkus, Ktor, Android JVM modules, JUnit, Mockito, Kotest, ktlint, detekt, or JVM
  CLI/services. Emphasizes JDK toolchains, null-safety, fast focused Gradle/Maven
  feedback, deterministic formatting, and minimal dependencies. NOT for JavaScript/TypeScript,
  C#/.NET, Python, shell scripts, or infra-only work.
name: writing-java-kotlin
---

<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Java and Kotlin Development

Use only for Java/Kotlin JVM code and JVM build files. Follow the project's JDK,
Kotlin, Gradle/Maven, framework, test stack, formatter, static-analysis config,
and local conventions.

## Read First

Read [principles.md](references/principles.md) before writing, changing, or reviewing Java/Kotlin code. Read conditional references only when the change touches that area.

## Conditional References

- [patterns.md](references/patterns.md) — package/module layout, Spring/Ktor/service boundaries, nullability, concurrency, persistence, and build seams.
- [testing.md](references/testing.md) — adding or reshaping JUnit, Kotest, Mockito/MockK, Spring, or Gradle/Maven tests; keep the local loop fast.
- [linting.md](references/linting.md) — Gradle/Maven toolchains, formatters, ktlint, detekt, Spotless, and slow-check policy.
- [cli.md](references/cli.md) — writing or changing JVM CLIs.

## Project Baseline

- Inspect `gradle/wrapper/gradle-wrapper.properties`, `settings.gradle*`, `build.gradle*`, `pom.xml`, `.mvn/`, `gradle.properties`, CI, and nearby code before using version-specific Java, Kotlin, or plugin behavior.
- Prefer the project wrapper: `./gradlew` before global `gradle`; `./mvnw` before global `mvn`.
- Use the configured Java toolchain and Kotlin `jvmToolchain`. Do not assume the shell's newest JDK is the compile target.
- Prefer the JDK/Kotlin stdlib and existing dependencies before adding a library.
- Keep domain code free of framework, persistence, HTTP, and DI types unless the project already chose that coupling.

## Version-Gated APIs

- Java 21+: records, sealed types, pattern matching, switch expressions, and virtual threads are available when the project toolchain allows them.
- Java 25+: treat new platform APIs as available only when Gradle/Maven toolchains and CI target 25 or newer.
- Preview features require explicit user or project approval and a visible compiler/test flag.
- Kotlin: follow the configured Kotlin language/API version. Do not use a Kotlin 2.x feature unless the build already enables it.

## Comments, Javadoc, and KDoc

- Use Javadoc or KDoc for visible public APIs when the project expects generated docs.
- Keep API docs to a useful summary, contract, edge case, or effect. Do not restate names and signatures.
- Omit comments for simple obvious getters, overrides, and data holders when there is nothing useful to add.
- Add implementation comments only for non-obvious constraints, invariants, side effects, tradeoffs, or framework quirks.
- Keep comments short. Move longer rationale to docs, issue links, or design notes.
- Do not comment obvious code.
- Keep tests readable without comments; add one only for unobvious fixtures, timing, concurrency, framework setup, or regression context.

## Verification

Run focused module tests and format/lint while editing, then the project-configured build, tests, lint, static analysis, and formatting checks before final output. Prefer Gradle/Maven test filtering over full-suite runs in the hot loop.

If a check is unavailable, state that and run the closest configured gate. If a
check fails, quote the failure, diagnose the cause, fix one issue, and rerun the
relevant check.

## Failure Cases

- No clear JVM root: locate the nearest `settings.gradle*`, `build.gradle*`, or `pom.xml` before choosing commands or package names.
- Unknown JDK or Kotlin target: inspect toolchains, compiler options, CI, and wrapper versions before using newer APIs or syntax.
- New dependency requested: confirm the JDK/Kotlin stdlib or existing dependencies cannot meet the requirement.
- Slow checks by default: switch to focused Gradle/Maven filters or file-scoped format/lint; reserve broad checks for final verification.
- Broad or risky edit: state the risk and ask before acting. Do not run destructive commands.

## Final Response

Include:

- changed files
- checks run and results
- checks skipped with reasons
- remaining risks or follow-ups
