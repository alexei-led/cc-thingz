# Java and Kotlin fix reference

Use for Java/Kotlin JVM defect fixes. The host skill owns the full fix workflow; this file adds language-specific repro commands and key failure patterns.

## Repro and narrow loop

Find the fastest reliable failing signal first:

```bash
./gradlew :module:test --tests 'com.example.FailingTest' --info
./gradlew :module:test --tests '*FailingTest'
./mvnw -q -pl module -Dtest=FailingTest test
./mvnw -q -Dtest=FailingTest test
./gradlew compileJava compileKotlin
```

Use the nearest module and test class filter while editing. Run `./gradlew build` or `./mvnw verify` before final output.

## Key failure patterns

- `NullPointerException` from unchecked Kotlin platform types (`T!`) or Java nulls crossing API boundaries.
- Kotlin `!!` on a nullable that can genuinely be null; fix the source, not the assertion.
- Coroutine scope leaked: `GlobalScope` launch or `runBlocking` in production code hiding cancellation.
- Spring bean circular dependency or missing `@Transactional` boundary causing `LazyInitializationException`.
- Thread safety: `HashMap` used from multiple threads without synchronization; shared mutable state in Spring singleton beans.
- `InterruptedException` swallowed silently; restore the interrupt flag or propagate.

## Verification

Before claiming fixed:

- Failing test or repro no longer fails.
- `./gradlew compileJava compileKotlin` (or `./mvnw compile`) exits clean.
- If build files changed, `./gradlew build` or `./mvnw package -DskipTests` exits clean.
- ktlint and detekt produce no new errors for Kotlin changes.
