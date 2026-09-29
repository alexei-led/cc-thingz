# Java and Kotlin Linting

- Spotless for deterministic formatting: `google-java-format` for Java, ktlint for Kotlin. Don't add a formatter that conflicts with existing config.
- detekt for Kotlin static analysis when the project has rules or accepts the default profile.
- Run Error Prone, Checkstyle, PMD, SpotBugs, and ArchUnit only when the task calls for them, not on every edit.

```bash
google-java-format -i src/main/java/com/example/Foo.java
ktlint --format src/main/kotlin/com/example/Foo.kt
detekt --input src/main/kotlin/com/example/Foo.kt
./gradlew spotlessApply detekt test
```

- Format before reporting style issues; fix findings at the cause, and ask before weakening a static-analysis rule.
- Keep generated, vendored, build, and annotation-processor output out of lint targets.
