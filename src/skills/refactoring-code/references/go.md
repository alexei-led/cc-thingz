# Go Refactoring Caveats

- `gopls rename` updates cross-package callers; it misses string references (route strings, struct tags, reflection, generated protobuf names), so search those separately.
- Renaming an exported identifier breaks external importers; keep a deprecated alias when the package is public.
- Moving a type changes its import path and every qualified reference.
- Extracting an interface can hide methods a caller used on the concrete type.
- Moving files can reorder `init()` side effects.
- Renaming a struct field changes its JSON/YAML/TOML key unless a tag pins it.
- Add `-race` to the safety gate when the change touches goroutines or shared state.
