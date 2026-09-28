# C# Refactoring Caveats

- IDE/Roslyn rename misses string routes, DI registrations by name, and reflection lookups; search for those.
- Renaming a public type, member, or namespace breaks binary consumers; add `[Obsolete]` shims.
- Namespace moves change fully qualified names used by reflection, DI scanning, JSON `$type` discriminators, and mapping configs.
- Extracting an interface moves the DI registration site; update `AddScoped`/`AddTransient`/`AddSingleton` calls and injection points.
- Refactored signatures can shift nullable analysis for callers; review `?` and `!` at the new boundary.
- Do not hand-edit generated partial classes (EF, source generators, gRPC); change the generator input.
