# Go Documentation

Use this only for Go files. The host skill owns scope, editing, and verification.

## Public API docs

- Exported packages, types, functions, methods, constants, and variables need GoDoc when they are part of the public API.
- Start comments with the exported symbol name.
- Document behavior, parameters only when not obvious from types, return values,
  errors, side effects, concurrency constraints, and compatibility guarantees.
- Add `Deprecated:` with a migration path for deprecated symbols.
- Put package comments in `doc.go` or the primary package file.

Good:

```go
// CreateUser creates a user and returns validation or conflict errors when the
// email is invalid or already assigned.
func CreateUser(ctx context.Context, req CreateUserRequest) (*User, error)
```

Avoid:

```go
// CreateUser creates a user.
func CreateUser(ctx context.Context, req CreateUserRequest) (*User, error)
```

## Comments

Keep comments that explain:

- business rules or invariants
- external API limits
- concurrency or ordering requirements
- surprising constraints or trade-offs

Delete comments that restate code.

## Tests

Prefer descriptive test names and table cases over comments. Keep a test comment
only when it explains non-obvious external behavior or why an edge case matters.

## README and examples

- `go install`, `go get`, and examples must match the current module and API.
- Examples should compile when practical.
- Architecture docs should cite package paths and stable boundaries, not every file.

## Checks

Prefer configured project checks. If available, use narrow docs or Go checks:

```bash
gofmt -w <files>
go test ./...
golangci-lint run --enable=godot,godoclint,revive ./...
```

If a tool is missing, inspect exported symbols manually and report the gap.
