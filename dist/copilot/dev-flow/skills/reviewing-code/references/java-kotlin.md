# Java and Kotlin Review Focus

Use writing-java-kotlin for toolchain commands. Check `build.gradle*`,
`pom.xml`, and toolchain settings before any version-gated claim.

- Kotlin platform types (`T!`) and `!!` at Java interop boundaries; missing nullability annotations there.
- Coroutines: `GlobalScope`, lost cancellation, blocking calls inside `suspend` functions.
- `InterruptedException` swallowed without restoring the interrupt flag.
- JPA/Hibernate: lazy collections touched outside a transaction, N+1 in loops, entities leaking across API boundaries instead of DTOs.
- Jackson `@JsonTypeInfo` or default typing enabling polymorphic deserialization; visibility changes exposing fields.
- SpEL built from user input; JPQL/HQL concatenation; XML parsers without external-entity processing disabled (XXE).
- Transaction boundaries missing or too broad; unclosed streams, connections, or executors.
- Full `@SpringBootTest` for logic a unit or slice test covers.
- `javax.*` and `jakarta.*` mixed in one module; Java 21 or Kotlin 2 features used on an older toolchain.
