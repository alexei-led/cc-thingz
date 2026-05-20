# ast-grep Rule Reference

Use this reference when a structural code search needs more than a one-line
`ast-grep run --pattern ...` query. ast-grep rules match AST nodes by shape,
relationship, and logical filters.

## Rule Object Basics

A rule object is usually YAML. Every field is optional, but at least one
positive matcher such as `pattern` or `kind` must appear.

A node matches when it satisfies every field in the rule object. That is an
implicit AND. Use `all` when execution order matters, especially when later
rules depend on metavariables captured earlier.

## Rule Categories

- **Atomic rules**: Match one node by intrinsic properties such as `pattern`,
  `kind`, `regex`, `nthChild`, or `range`.
- **Relational rules**: Match by relationship to other nodes: `inside`, `has`,
  `precedes`, or `follows`.
- **Composite rules**: Combine other rules with `all`, `any`, `not`, or
  `matches`.

## Rule Fields

- **`pattern`**: Atomic. Matches AST node shape by code pattern.
  Example: `pattern: console.log($ARG)`.
- **`kind`**: Atomic. Matches a Tree-sitter node kind.
  Example: `kind: call_expression`.
- **`regex`**: Atomic. Matches the node text with Rust regex.
  Example: `regex: ^[a-z]+$`.
- **`nthChild`**: Atomic. Matches a child position within its parent.
  Example: `nthChild: 1`.
- **`range`**: Atomic. Matches character-based start and end positions.
- **`inside`**: Relational. Target node must be inside a node matching the
  sub-rule. Use `stopBy: end` for deep parent traversal.
- **`has`**: Relational. Target node must have a descendant matching the
  sub-rule. Use `stopBy: end` for deep child traversal.
- **`precedes`**: Relational. Target node must appear before a node matching
  the sub-rule.
- **`follows`**: Relational. Target node must appear after a node matching the
  sub-rule.
- **`all`**: Composite. Every sub-rule must match.
- **`any`**: Composite. At least one sub-rule must match.
- **`not`**: Composite. The sub-rule must not match.
- **`matches`**: Composite. References a reusable utility rule by ID.

## Atomic Rules

### pattern

String form:

```yaml
pattern: console.log($ARG)
```

Object form, useful when parsing context or strictness matters:

```yaml
pattern:
  selector: field_definition
  context: class { $F }
```

Common object keys:

- `selector` — choose which node in the parsed pattern is the actual match.
- `context` — provide surrounding code so the pattern parses correctly.
- `strictness` — tune matching. Common values include `cst`, `smart`, `ast`,
  `relaxed`, and `signature`.

### kind

`kind` matches the Tree-sitter node kind for the language grammar. It is useful
when a plain pattern is ambiguous.

```yaml
kind: call_expression
```

Use `--debug-query=cst` or `--debug-query=ast` to inspect kind names.

### regex

`regex` matches the full text of a candidate node using Rust regex syntax. Pair
it with a positive structural matcher such as `kind` when possible.

```yaml
rule:
  kind: identifier
  regex: "^use[A-Z]"
```

### nthChild

`nthChild` matches by 1-based sibling position. By default, ast-grep counts
named nodes.

Forms:

- Number: `nthChild: 1`.
- An+B string: `nthChild: 2n+1`.
- Object with `position`, `reverse`, and `ofRule`.

Example:

```yaml
nthChild:
  position: 1
  reverse: true
  ofRule:
    kind: argument
```

### range

`range` matches character positions. Lines and columns are zero-based. `start`
is inclusive; `end` is exclusive.

```yaml
range:
  start: { line: 0, column: 0 }
  end: { line: 0, column: 10 }
```

## Relational Rules

### inside

The target node must be inside a node that matches the `inside` sub-rule.

```yaml
rule:
  pattern: console.log($$$)
  inside:
    kind: method_definition
    stopBy: end
```

### has

The target node must contain a descendant that matches the `has` sub-rule.

```yaml
rule:
  kind: function_declaration
  has:
    pattern: await $EXPR
    stopBy: end
```

### precedes and follows

`precedes` requires the target to appear before a matching node. `follows`
requires it to appear after one.

```yaml
rule:
  pattern: return $VALUE
  follows:
    pattern: if ($COND) { $$$ }
    stopBy: end
```

### stopBy

`stopBy` controls when relational traversal stops.

- `neighbor` — default. Stops when the immediate surrounding node does not
  match.
- `end` — searches to the end of the direction: root for `inside`, leaf for
  `has`.
- Rule object — stops when a surrounding node matches that rule.

Use `stopBy: end` unless you have a reason not to. The default is stingy.

### field

`field` restricts `inside` or `has` to a named child field.

```yaml
rule:
  kind: binary_expression
  has:
    field: operator
    pattern: $$OP
```

## Composite Rules

### all

Every sub-rule must match. Use it to make rule order explicit.

```yaml
rule:
  all:
    - kind: call_expression
    - pattern: console.log($ARG)
```

### any

At least one sub-rule must match.

```yaml
rule:
  any:
    - pattern: console.log($$$)
    - pattern: console.warn($$$)
    - pattern: console.error($$$)
```

### not

The sub-rule must not match.

```yaml
rule:
  not:
    pattern: console.log($ARG)
```

### matches

References a utility rule by ID.

```yaml
utils:
  is-console:
    any:
      - pattern: console.log($$$)
      - pattern: console.error($$$)
rule:
  matches: is-console
```

## Metavariables

### `$VAR`

Captures one named AST node.

Valid examples:

- `$META`
- `$META_VAR`
- `$_`

Invalid examples:

- `$invalid`
- `$123`
- `$KEBAB-CASE`

Reuse means equality. `$A == $A` matches `a == a`, not `a == b`.

### `$$VAR`

Captures one unnamed node, such as punctuation or an operator.

```yaml
rule:
  kind: binary_expression
  has:
    field: operator
    pattern: $$OP
```

### `$$$VAR`

Captures zero or more AST nodes.

Examples:

- `console.log($$$)` matches any number of arguments.
- `function $NAME($$$ARGS) { $$$BODY }` matches variable parameters and body.

### Non-capturing metavariables

Names starting with `_` are not captured and need not equal each other.

```yaml
pattern: $_FUNC($_ARG)
```

### Metavariable limits

A metavariable must be the whole AST node text. These do not work as captures:

- `obj.on$EVENT`
- `"Hello $WORLD"`
- `a $OP b`
- `$jq`

## Common Rules

### Functions containing await

```yaml
rule:
  kind: function_declaration
  has:
    pattern: await $EXPR
    stopBy: end
```

### console calls inside class methods

```yaml
rule:
  pattern: console.log($$$)
  inside:
    kind: method_definition
    stopBy: end
```

### Async functions with await but no try/catch

```yaml
rule:
  all:
    - kind: function_declaration
    - has:
        pattern: await $EXPR
        stopBy: end
    - not:
        has:
          pattern: try { $$$ } catch ($E) { $$$ }
          stopBy: end
```

### Multiple console methods

```yaml
rule:
  any:
    - pattern: console.log($$$)
    - pattern: console.warn($$$)
    - pattern: console.error($$$)
    - pattern: console.debug($$$)
```

## Troubleshooting

- Rule does not match: run `--debug-query=pattern` on the pattern.
- Wrong node kind: run `--debug-query=cst` or `--debug-query=ast` on a target
  snippet and inspect kind names.
- Relational rule misses nested code: add `stopBy: end`.
- Metavariable does not capture: ensure the metavariable is the whole AST node.
- Pattern is too clever: split it with `all` and test one condition at a time.

## Sources

Adapted from the ast-grep agent skill at
`https://github.com/ast-grep/agent-skill/tree/main/ast-grep/skills/ast-grep`
and ast-grep documentation for `run`, `scan`, `--inline-rules`, and
`--debug-query`.
