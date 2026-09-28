# Java and Kotlin Tests

Use writing-java-kotlin for toolchain commands. Identify the framework (JUnit 5,
JUnit 4, TestNG, Kotest), assertion library, and mock library from nearby tests.

- Filter to one module and class in the edit loop (`:module:test --tests`, `-pl module -Dtest=`); run the full build only at the end or for cross-module changes.
- No full `@SpringBootTest` for pure logic. Use a slice (`@WebMvcTest`, `@DataJpaTest`) or no context.
- Testcontainers, real databases, and browser tests belong in a separate Gradle or Maven profile.
- Coroutines: `runTest` with a test scheduler; not `runBlocking` in new tests.
- Do not mix Mockito and MockK in one test class. `verify` only side effects that matter; no `any()` on business-critical arguments.
- `@ParameterizedTest`/`@MethodSource` or Kotest `forAll` for case matrices; AssertJ-style `assertThat` for clearer failures.
- Shared static caches or singleton state across tests cause flakes; reset or isolate them.
