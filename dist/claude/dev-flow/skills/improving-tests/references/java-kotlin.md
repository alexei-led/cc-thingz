# Java and Kotlin test slice

Use this only for JVM test work. The host skill owns scope, workflow, and output.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
./gradlew :module:test --tests 'com.example.FooTest'
./gradlew :module:test --tests '*FooTest'
./gradlew :module:test --tests 'com.example.FooTest.methodName'
./mvnw -q -pl module -Dtest=FooTest test
./mvnw -q -pl module -Dtest='FooTest#methodName' test
./mvnw -q -Dtest=FooTest test
```

Use full `./gradlew test` or `./mvnw test` only for final verification or cross-module changes. Avoid running the full build just to run tests.

## Learn project patterns

Before changing tests:

- Read 2-3 nearby test files to identify the framework (JUnit 5, JUnit 4, TestNG, Kotest) and assertion library (AssertJ, Truth, Hamcrest, or built-in).
- Check for shared test fixtures, `@TestConfiguration` beans, `@ExtendWith` extensions, factory helpers, and project-specific slice annotations (`@WebMvcTest`, `@DataJpaTest`, etc.).
- Follow the existing mock library (Mockito, MockK) and argument-matching conventions unless they are the problem.

## Test shape

- Test public behavior through services, repositories, controllers, CLI commands, or other stable seams.
- Use parameterized tests (`@ParameterizedTest`, `@MethodSource`, Kotest `forAll`) for readable case matrices.
- Use `async Task`-equivalent patterns for coroutines: `runTest` (coroutines-test), `runBlocking` (avoid in new tests; prefer `runTest`).
- Mock only system boundaries: network, filesystem, time, randomness, subprocesses, databases, and external services. Prefer real domain collaborators or small fakes.
- Avoid sleeps. Use fake clocks (`TestCoroutineScheduler`, `InstantTaskExecutorRule`), latches, `CountDownLatch`, or deterministic synchronization.

## Speed waste

- Do not start a full Spring application context (`@SpringBootTest`) for pure business logic; use a slice annotation (`@WebMvcTest`, `@DataJpaTest`) or no context at all.
- Keep Testcontainers, real database, and browser-level tests in integration tiers with a separate Gradle/Maven profile or build tag; do not run them in every focused loop.
- Avoid classpath-wide discovery when a module or class filter suffices.
- Keep coverage, mutation, detekt, and static-analysis tasks out of the focused feedback loop unless the task is about them.

## Mocks and assertions

- Use Mockito `verify` only for side effects that matter to the test, not to assert call count for every internal method.
- Use MockK `verify` in Kotlin tests consistently — do not mix Mockito and MockK in the same test class.
- Prefer `assertThat(...).isEqualTo(...)` (AssertJ) or equivalent over `assertEquals`; it produces clearer failure messages.
- Do not use `any()` matchers on business-critical arguments; match the exact expected value or a meaningful subset.

## Review focus

Flag:

- tests that boot a full application context for logic that needs none
- happy-path-only tests for service, repository, or handler logic with meaningful error paths
- missing success, failure, null/empty, boundary, cancellation, or regression cases
- `@MockBean` or mock setups that hide contracts or accept any value
- shared mutable test state or static caches that cause flakes
- real sleeps or `Thread.sleep` in tests
- tests coupled to internal implementation instead of the public seam

## Failure handling

- Test runner failures are blocking.
- If no test module is obvious for a source edit, use the nearest module with a test source set.
- If no JVM test target exists, report that before other findings.
