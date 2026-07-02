# Java and Kotlin linting

Use when changing JVM formatter, linter, static-analysis, toolchain, or fast-feedback commands.

## Preferred project setup

- Prefer Gradle wrapper and Maven wrapper over globally installed Gradle/Maven.
- Configure Java toolchains and Kotlin `jvmToolchain`; do not rely on the agent shell's `JAVA_HOME`.
- Prefer Spotless for deterministic formatting in Gradle/Maven builds:
  - Java: `google-java-format` through Spotless or direct CLI.
  - Kotlin: ktlint through Spotless or direct CLI.
- Use detekt for Kotlin static analysis when the project already has rules or accepts the default profile.
- Keep Error Prone, Checkstyle, PMD, SpotBugs, ArchUnit, and coverage/mutation checks out of the post-edit hot path unless the task is about those checks.

## Fast hook commands

File-scoped local commands are the fastest edit loop:

```bash
google-java-format -i src/main/java/com/example/Foo.java
ktlint --format src/main/kotlin/com/example/Foo.kt
detekt --input src/main/kotlin/com/example/Foo.kt
```

Project-scoped commands are final or fallback checks:

```bash
./gradlew spotlessApply detekt test
./gradlew :module:test --tests '*FooTest'
./mvnw -q spotless:apply test
./mvnw -q -Dtest=FooTest test
```

## Policy

- Auto-format before reporting style issues.
- Do not add a formatter that conflicts with existing `.editorconfig`, Spotless, ktlint, IntelliJ, or Checkstyle rules.
- Do not weaken static-analysis rules to pass a scoped change. Fix the code or ask before changing policy.
- Report missing tools directly and run the nearest configured command.
- Keep generated code, vendored code, build output, and annotation-processor output out of lint targets.
