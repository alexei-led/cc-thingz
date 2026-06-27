# Java and Kotlin refactoring reference

Use for Java/Kotlin behavior-preserving refactors. The host skill owns the scope-mapping workflow and output contract; this file adds language-specific mapping tools, safety gates, and caveats.

## Scope mapping

Before editing:

- Use IntelliJ IDEA / IDE rename/move for symbol renames — they update all usages including generated code, Spring bean names, and Kotlin extension receivers.
- Use `rg` for string-based references: `@RequestMapping` paths, Spring bean names in XML/YAML, reflection-based `Class.forName`, serialization `@JsonTypeName`, and Kotlin companion object constants used as string keys.
- For package or class moves, check all import statements: `rg 'import old\.package\.ClassName'`.
- For public API changes, check all callers across Gradle/Maven modules; a module-level `./gradlew :module:compileJava` catches cross-module compile errors quickly.

## Verification gate

```bash
./gradlew compileJava compileKotlin
./gradlew test
./mvnw -q compile test
```

Run compilation before each batch to catch errors early. Run the full test suite before final output.

## Key caveats

- Renaming a public class or method is a binary and source breaking change; add `@Deprecated(since=...)` aliases for library code.
- Moving a class changes its fully qualified name — check Spring `@ComponentScan`, `@MapperScan`, Hibernate `hbm2ddl` entity names, and Jackson `@JsonTypeName` or `@Type` discriminators.
- Kotlin `data class` renames change the component function names (`component1()`, `component2()`) used in destructuring; audit all destructuring call sites.
- Extracting an interface from a Spring `@Service` or `@Repository` changes the DI proxy type; ensure injection points use the interface type.
- Gradle/Maven module renames change artifact coordinates; update all consuming `build.gradle` / `pom.xml` dependency declarations.
