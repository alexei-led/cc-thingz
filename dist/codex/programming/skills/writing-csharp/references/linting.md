# C# /.NET Linting

Use the project's command first. Edit loop, scoped to the nearest project or solution:

```bash
dotnet format path/to/App.csproj --include src/Orders/OrderService.cs
dotnet format path/to/App.csproj --verify-no-changes
dotnet build path/to/App.csproj
```

- Run `dotnet build` when formatting alone cannot prove the change, and after edits to `.csproj`, `.props`, or `.targets`.
- Run the broader solution build before finishing when the change touches shared props, targets, package references, or public contracts.
- Keep nullable, analyzer, and `TreatWarningsAsErrors` policy intact unless the task changes that policy. Fix warnings at the source rather than with `#pragma` or suppression attributes.
- Exclude generated and vendor code through project config, not ad hoc filters.
- If lint is slow, split a hot-path command from the full gate; do not weaken the full gate without approval.
