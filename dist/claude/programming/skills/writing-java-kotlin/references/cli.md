# Java and Kotlin CLI patterns

Use when writing or changing JVM command-line tools.

## Shape

- Keep `main` thin: parse args, configure logging, wire dependencies, call one command/service, map result to exit code.
- Keep business behavior in testable classes or functions outside the CLI framework.
- Use the project's existing CLI stack: picocli, Clikt, Spring Shell, args4j, custom parser, or plain `main`.
- Do not add a CLI framework for a tiny internal command unless parsing, help text, subcommands, or validation justify it.

## Input and output

- Validate flags, env vars, files, and stdin before domain use.
- Write machine-readable output to stdout and diagnostics to stderr.
- Keep exit codes documented and stable.
- Do not print secrets, tokens, or full credentials in logs or error messages.

## Runtime

- Pass cancellation, deadlines, or interruption through long-running work.
- Close HTTP clients, file handles, DB pools, and executors when the process owns them.
- For Kotlin CLIs, keep coroutine scopes structured and close dispatchers created by the CLI.

## Testing

- Test command behavior through the public command entrypoint or parser seam.
- Capture stdout, stderr, and exit code.
- Use temp directories/files for filesystem behavior.
- Keep slow external calls behind fakes or testcontainers only when integration behavior is required.
