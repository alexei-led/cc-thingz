# C# /.NET CLI patterns

Read before writing or changing .NET CLIs.

## Framework choice

- Use the existing CLI framework when one is already in the project.
- For small tools, the BCL is often enough.
- Use `System.CommandLine`, Spectre.Console, or another CLI package only when the project already uses it or the command surface justifies it.
- Do not add a package only for cosmetic output.

## Boundaries

- Keep argument parsing, prompts, output formatting, and exit-code mapping in the CLI layer.
- Keep business behavior in methods that accept typed input and return typed results.
- Keep `Program.cs` or top-level statements thin.
- Use cancellation tokens for long-running or external work.

## Output and errors

- Write requested data to stdout and diagnostics to stderr.
- Keep JSON or other machine-readable output stable.
- Map expected failures to clear messages and exit codes at the boundary.
- Avoid burying domain errors in broad catch blocks.

## Tests

- Test command handlers or `Main`/`Run` seams without shelling out when possible.
- Assert exit code, stdout, stderr, and side effects.
- Use temp directories and fakes for filesystem or process behavior.
- Cover parse failures, cancellation, config precedence, and machine-readable output when relevant.
