# Go refactoring reference

Use for Go behavior-preserving refactors. The host skill owns the scope-mapping workflow and output contract; this file adds language-specific mapping tools, safety gates, and caveats.

## Scope mapping

Before editing:

- Use `gopls rename` for symbol renames — it updates all callers including cross-package uses.
- Use `rg` or `grep` for string-based references (route strings, field tags, generated protobuf names) and for interface method names used in reflection.
- For package moves or renames, check all `import` statements across the module with `rg '"old/package/path"'`.
- For exported interface changes, check all implementations across the repo: `rg 'func.*MethodName'`.

## Verification gate

```bash
go build ./...
go vet ./...
go test ./...
```

Run `go build ./...` before each batch to catch compile errors early. Run `go test ./...` before final output. Add `-race` for changes touching goroutines or shared state.

## Key caveats

- Renaming an exported identifier is a breaking API change for external module consumers; keep the old name as a deprecated alias when the package is publicly imported.
- Moving a type to a different package changes its import path and all type assertions that use its full name.
- Interface extraction changes the type seen by callers using concrete types; check if any caller depends on methods not in the interface.
- `init()` functions in moved files execute in package init order; moving them can change initialization side effects.
- Struct field renames break JSON/YAML/TOML tag keys unless the tag is explicitly set; check serialization at API and storage boundaries.
