# Java and Kotlin Refactoring Caveats

- IDE rename misses string references: `@RequestMapping` paths, bean names in XML/YAML, `Class.forName`, `@JsonTypeName`, and constants used as keys.
- Renaming a public class or method breaks source and binary consumers; add `@Deprecated` aliases in library code.
- Moving a class changes its fully qualified name, which `@ComponentScan`, `@MapperScan`, Hibernate entity names, and Jackson type discriminators depend on.
- Reordering Kotlin `data class` constructor properties changes positional `componentN()` destructuring; audit destructuring sites.
- Extracting an interface from a Spring `@Service` or `@Repository` changes the proxy type; inject the interface.
- Renaming a Gradle or Maven module changes artifact coordinates for every consumer.
