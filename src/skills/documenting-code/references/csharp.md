# C# /.NET documentation

Use this only for C# and .NET files. The host skill owns scope, editing, and verification.

## Public API docs

- Use XML doc comments (`///`) on every public type, member, constructor, and property when it is part of a public or internal library API.
- Write `<summary>` that describes what the member does and why a caller would use it, not just restates the name.
- Add `<param>`, `<returns>`, `<exception>`, and `<remarks>` only when they add information that the signature and type system do not already convey.
- Use `<see cref="..."/>` for cross-references to related types or members.
- Mark deprecated public members with `<obsolete>` and add a `[Obsolete]` attribute with a migration note.

Good:

```csharp
/// <summary>
/// Creates a user account and returns the new user ID, or throws
/// <see cref="DuplicateEmailException"/> when the email is already registered.
/// </summary>
/// <param name="request">Validated registration request; must not be null.</param>
/// <param name="ct">Cancellation token for the underlying persistence call.</param>
/// <returns>The assigned user ID.</returns>
/// <exception cref="DuplicateEmailException">Email is already registered.</exception>
public Task<UserId> CreateUserAsync(CreateUserRequest request, CancellationToken ct)
```

Avoid:

```csharp
/// <summary>Creates a user.</summary>
public Task<UserId> CreateUserAsync(CreateUserRequest request, CancellationToken ct)
```

## Comments

Keep comments that explain:

- why a `CancellationToken` scope or `ConfigureAwait(false)` choice is deliberate
- non-obvious nullable flow (when `!` or a suppression is intentional and safe)
- business invariants, concurrency ordering, or idempotency requirements
- accepted trade-offs such as sync-over-async or intentional data-loss paths

Delete comments that restate code, paraphrase obvious property accessors, or describe the `what` visible from types and names.

## Tests

Prefer descriptive test method names and parameterized `Theory` / `TestCase` cases over inline comments. Keep a comment only when it explains non-obvious external behavior or a tricky edge case that the name cannot convey.

## README and project docs

- `dotnet build`, `dotnet test`, and example commands must match the current SDK, project, and target framework.
- Keep NuGet package names, version ranges, and install commands current.
- Architecture docs should cite stable boundaries (namespaces, projects, interface contracts), not internal class layouts.

## Checks

Prefer configured project checks. If available, use narrow docs or .NET checks:

```bash
dotnet build path/to/App.sln
dotnet format path/to/App.sln --verify-no-changes
dotnet test path/to/Tests.csproj
```

If a tool is missing, inspect exported public members manually and report the gap.
