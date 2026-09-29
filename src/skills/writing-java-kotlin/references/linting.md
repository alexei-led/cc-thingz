# Java and Kotlin Linting

- Spotless for deterministic formatting: `google-java-format` for Java, ktlint for Kotlin. Do not add a formatter that conflicts with existing `.editorconfig`, Spotless, ktlint, IntelliJ, or Checkstyle rules.
- detekt for Kotlin static analysis when the project has rules or accepts the default profile.
- Run Error Prone, Checkstyle, PMD, SpotBugs, and ArchUnit only when the task calls for them, not on every edit.

File-scoped edit loop:

```bash
google-java-format -i src/main/java/com/example/Foo.java
ktlint --format src/main/kotlin/com/example/Foo.kt
detekt --input src/main/kotlin/com/example/Foo.kt
```

Project-scoped gate:

```bash
./gradlew spotlessApply detekt test
./mvnw -q spotless:apply test
```

- Format before reporting style issues.
- Fix findings at the cause. Ask before weakening static-analysis rules.
- Keep generated, vendored, build, and annotation-processor output out of lint targets.
