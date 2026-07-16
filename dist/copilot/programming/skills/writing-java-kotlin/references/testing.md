# Java and Kotlin testing

Read before adding or reshaping JVM tests.

## Defaults

- Use the project's test framework: JUnit 5/Jupiter, JUnit 4, TestNG, Kotest, Spek, Spring test, Mockito, MockK, AssertJ, Truth, or Hamcrest. Do not switch frameworks in scoped work.
- Test behavior through public classes, services, handlers, controllers, repositories, CLIs, or other stable seams.
- Cover success, failure, boundary, cancellation, concurrency, serialization, and regression behavior when relevant.
- Avoid comments in tests. Add one only for unobvious fixtures, timing, concurrency, framework setup, or regression context.

## Fast commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
./gradlew :module:test --tests 'com.example.FooTest'
./gradlew test --tests '*FooTest'
./gradlew :module:test
./mvnw -q -pl module -Dtest=FooTest test
./mvnw -q -Dtest=FooTest test
```

Keep the edit loop focused on the nearest module and matching test class. Run the broader configured suite before final output when the change crosses modules, build logic, serialization contracts, or framework wiring.

## Test style

- Prefer parameterized tests for input/output matrices when they stay readable.
- Use one assertion style consistently with nearby tests.
- Name tests by behavior, not implementation detail.
- Assert visible behavior, returned values, thrown exceptions, emitted events, persisted state, HTTP status/body, and external side effects.
- Delete shallow duplicate tests once stronger boundary tests cover the same path.

## Mocks and integration seams

- Mock only system boundaries: network, filesystem, time, randomness, subprocesses, databases, queues, and external services.
- Prefer real domain collaborators or small fakes when cheaper and clearer than mocks.
- For Spring or framework HTTP behavior, use the project's existing slice/integration-test harness before adding a new one.
- For database code, prefer testcontainers, disposable local DBs, in-memory DBs, or the project's existing test seam over mocking query chains.

## Coroutines, threads, and time

- Kotlin coroutines: use the project's coroutine test library and test dispatcher. Avoid real sleeps.
- Java concurrency: use deterministic synchronization, timeouts, and executor control. Do not rely on thread scheduling.
- Restore interrupt state or assert cancellation behavior when testing interruption.

## Fast feedback

- Keep browser, end-to-end, coverage, mutation, and slow integration tiers off the hot path unless they are the task.
- Avoid classpath-wide or full-build commands during edits when Gradle/Maven filters can target one module or class.
- Keep Spring context startup and Testcontainers usage out of unit tests unless behavior needs real wiring.
- Run broader project checks before final output when the change affects shared APIs or build files.
