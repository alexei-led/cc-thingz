# Go CLI patterns

Read before writing or changing Go CLIs.

## Framework choice

- Use the existing CLI framework when one is already in the project.
- Use stdlib `flag` for small single-command tools.
- Use Cobra for many subcommands, shell completions, generated docs, or kubectl/gh-style command trees.
- Use urfave/cli for simpler multi-command tools that need less structure.
- Avoid adding Viper unless the project already uses it or needs its config-source behavior.

## Boundaries

- Keep argument parsing, prompts, output formatting, and exit-code mapping in the CLI layer.
- Put business behavior in functions that accept typed input and return typed output plus `error`.
- Keep `main` thin: call `run`, print boundary errors, exit.
- Use `context.Context` from signal handling for long-running or cancelable commands.
- Apply config precedence in this order: flag, env, config file, default.

## Output

- Write data to stdout and diagnostics to stderr.
- Keep JSON, CSV, and other machine-readable formats stable.
- Do not mix logs into machine-readable stdout.
- Make destructive actions explicit and support dry-run when the command changes external state.

## Errors and exits

- Return errors from command logic; map them to messages and exit codes at the CLI boundary.
- Use `errors.Is` or typed errors only when boundary behavior branches on them.
- Keep user-facing errors concise. Preserve wrapped context for logs or verbose mode when useful.
- Avoid `log.Fatal`; return from `run`, finish cleanup, print at the boundary, then exit.

## Tests

- Test `run(args, stdin, stdout, stderr)` style seams instead of calling `os.Exit`.
- Assert exit code, stdout, stderr, and side effects.
- Use temp dirs and in-memory readers/writers for filesystem and I/O behavior.
- Include parse failures, config precedence, dry-run behavior, cancellation, and machine-readable output stability when relevant.
