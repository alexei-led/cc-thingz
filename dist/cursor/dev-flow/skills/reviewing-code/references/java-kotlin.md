# Java and Kotlin review reference

Host skill owns scope, severity, scoring, and output. This file adds Java/Kotlin JVM-specific evidence gathering and checks.

## Tool-enabled review

Run configured project tools only when the active role can execute commands. Prefer project commands when present.

Useful JVM gates:

```bash
./gradlew compileJava compileKotlin
./gradlew test
./gradlew detekt ktlintCheck
./mvnw -q verify
```

Treat tool output as evidence, then map it through the severity rubric. If a tool is missing or too slow, report the gap and continue source review. Do not install tools.

## Read-only review

When commands are unavailable, use supplied diff, file reads, and caller-supplied output. Follow direct callers for changed public classes, services, controllers, handlers, repositories, and DTO boundaries.

## Focus checks

Correctness:

- Nullability: unchecked Java platform types (`T!`) in Kotlin, missing `@NonNull`/`@Nullable` at Java/Kotlin interop boundaries, `!!` on a value that can genuinely be null.
- Kotlin coroutines: `GlobalScope` usage hiding structured concurrency, missing cancellation propagation, blocking calls inside `suspend` functions.
- Java virtual threads (21+): blocking operations that are acceptable in platform threads but should be reviewed for correctness with structured concurrency APIs.
- `InterruptedException` caught and swallowed without restoring the interrupt flag.
- Spring/Jakarta lazy-loading: `LazyInitializationException` from accessing collections outside an active session or transaction.
- Serialization: Jackson `@JsonIgnore` or visibility changes that expose or hide fields across REST boundaries; `@JsonTypeInfo` discriminators that may enable polymorphic deserialization.

Security:

- SQL injection from JPQL/HQL string concatenation or raw JDBC without parameterization.
- SpEL injection from user-controlled expressions in Spring `@Value` or `@Query`.
- Path traversal from user-controlled strings passed to `java.io.File` or `java.nio.Path` APIs.
- XXE from XML parsers (`DocumentBuilderFactory`, `SAXParserFactory`) without disabling external entity processing.
- Missing authorization at `@PreAuthorize`, method-level security, or explicit Spring Security checks.
- Secrets in logs, exception messages, build files, or test fixtures.

Reliability:

- Missing `CancellationToken`/timeout propagation for HTTP, DB, queue, and external service calls.
- Resource leaks: unclosed `InputStream`, `Connection`, `Session`, `Channel`, or `ExecutorService`.
- Transaction boundary missing or too broad, causing partial failures or long-held locks.
- Retry loop without cap, exponential backoff, or idempotency check.

Performance:

- N+1 queries from accessing lazy collections inside a loop without a join fetch.
- Hibernate/JPA entity passed across boundaries instead of DTOs, causing unexpected lazy load.
- `String` concatenation in loops; use `StringBuilder` or string templates.
- Unnecessary full collection load when a count, projection, or stream suffices.

Tests:

- Changed service or repository behavior without JUnit/Kotest coverage for success, failure, and edge cases.
- Bug fixes without a regression test at the public seam.
- Tests that boot a full Spring context for pure business logic that could use a unit test.

## Version-gated checks

Inspect `build.gradle*`, `pom.xml`, `toolchain` settings, and CI before applying version-specific claims.

- Java 21+: record classes, pattern matching, virtual threads, and sealed types are available when the toolchain allows them.
- Kotlin 2.x: K2 compiler and new language features may not be available in Kotlin 1.x projects; check the Kotlin version in the build.
- Jakarta EE 9+ renamed `javax.*` packages to `jakarta.*`; do not mix them.

## Failure handling

- Compile, test, or static-analysis failure in reviewed scope: Critical when confirmed by tool output.
- Ambiguous Spring or framework wiring behavior: use Needs review and name the missing configuration or bean scope.
- LSP or graph unavailable: note reduced cross-module coverage only when it affects the finding.
