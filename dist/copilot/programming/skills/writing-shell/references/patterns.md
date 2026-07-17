# Shell Patterns

## Shell selection

- POSIX `sh`: simple scripts, broad portability, containers, package hooks, and systems where Bash may be old or absent.
- Bash: arrays, associative arrays, `[[ ]]`, `pipefail`, regex matching, richer functions, and safer argument assembly.
- Zsh: interactive config, completions, or existing Zsh scripts only.
- Fish: interactive config/functions only unless the user explicitly wants Fish automation.

## Script shape

- Treat shell as glue. Move complex data modeling, business logic, or large data processing to Python, Go, TypeScript, or another project language.
- Start with a clear shebang and usage output.
- Keep top-level flow readable: parse args, validate inputs, perform work, report result.
- Use small functions for repeated behavior; pass values as arguments instead of relying on globals.
- Keep stdout stable when another tool consumes it. Send logs and diagnostics to stderr.
- Support `-h` or `--help` for user-facing scripts.

## Error handling and debugging

- For Bash, use strict mode when it fits: `set -euo pipefail`. Understand exceptions around conditionals and `&&`/`||` lists.
- For POSIX `sh`, use `set -eu`; handle pipeline failures explicitly when they matter.
- Add a debug flag or env var that enables tracing instead of leaving `set -x` on permanently.
- Quote diagnostic values and include enough context to identify the failing file, command, or resource.
- Prefer explicit status checks around commands that may fail normally.
- Use cleanup traps for temporary files, locks, and partial outputs.

## Safety

- Prefer explicit paths and resource names over broad globs.
- Validate required input before filesystem, network, or process changes.
- Use `mktemp` for temporary paths and trap cleanup.
- Avoid `eval`. Use case statements, arrays, or explicit dispatch.
- Avoid `curl | sh`; download, verify, and execute as separate steps when unavoidable.
- Use `--` before user-controlled operands when supported.
- For destructive actions, show candidates first and require confirmation unless the script is clearly non-interactive CI with explicit inputs.

## Portability

- Do not assume GNU-only flags on macOS.
- Prefer `printf` over `echo` when output portability matters.
- Avoid `date -d`, `readlink -f`, GNU-only `sed`, and GNU-only `grep` flags unless the dependency is documented.
- Prefer portable constructs for scripts with `/bin/sh` shebangs.
- Run `checkbashisms` when a `/bin/sh` script must stay POSIX.
- Keep Bash-only scripts under a Bash shebang; do not pretend they are POSIX.

## Data handling

- Do not parse JSON, YAML, CSV, XML, or INI with raw text filters when a structured parser is available.
- Use NUL-delimited pipelines for arbitrary filenames when possible.
- Avoid `for x in $(cmd)` for data with spaces, newlines, or glob characters.
- Use Bash arrays for command arguments instead of building command strings.

## Performance

- Avoid external commands in tight loops when a shell builtin or one batched command works.
- Batch file operations instead of spawning one process per file.
- Measure before optimizing. Use `hyperfine`, `time`, or focused fixtures when performance matters.
- Switch languages when the script becomes CPU-heavy, state-heavy, or hard to test.
