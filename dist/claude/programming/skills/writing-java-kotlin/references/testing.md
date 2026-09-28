# Java and Kotlin Testing

Use the project's test stack (JUnit 5, Kotest, TestNG, Mockito, MockK, AssertJ); do not switch in scoped work. Match nearby assertion style.

```bash
./gradlew :module:test --tests 'com.example.FooTest'
./gradlew test --tests '*FooTest'
./mvnw -q -pl module -Dtest=FooTest test
./mvnw -q -Dtest=FooTest test
```

- Edit loop: one module and matching test class. Run the broader suite when the change crosses modules, build logic, serialization contracts, or framework wiring.
- Spring HTTP behavior: the project's existing slice or integration harness. Keep Spring context startup and Testcontainers out of unit tests unless behavior needs real wiring.
- Database code: Testcontainers, a disposable DB, or the project's seam, not mocked query chains.
- Kotlin coroutines: `kotlinx-coroutines-test` (`runTest` with the test dispatcher's virtual time), never real sleeps.
- Java concurrency: control executors and synchronize deterministically; assert interrupt and cancellation behavior.
- Keep coverage, mutation, browser, and end-to-end tiers off the hot path unless they are the task.
