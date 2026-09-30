# Java and Kotlin Testing

Use the project's test stack (JUnit 5, Kotest, TestNG, Mockito, MockK, AssertJ); do not switch in scoped work. Match nearby assertion style.

```bash
./gradlew :module:test --tests 'com.example.FooTest'
./gradlew test --tests '*FooTest'
./mvnw -q -pl module -Dtest=FooTest test
./mvnw -q -Dtest=FooTest test
```

- Edit loop: one module and matching test class; run the broader suite when the change crosses modules or build logic.
- Database code: Testcontainers, a disposable DB, or the project's seam, not mocked query chains.
- Java concurrency: control executors and synchronize deterministically; assert interrupt and cancellation behavior.
