# Shell Testing and Quality Gates

## Gates

```bash
shfmt -d script.sh
shellcheck script.sh          # set --shell when the shebang is missing
checkbashisms script.sh       # /bin/sh scripts that claim POSIX
bats tests/                   # Bash-heavy projects
shellspec                     # POSIX or multi-shell behavior
```

- Semgrep shell rules for scripts that handle secrets, downloads, deletion, permissions, or user input.
- `bashate` only when the project already runs it. `shellharden` rewrites can change behavior; use it only with tests and a diff review.

## Test Design

- Drive the script through its entrypoint. Assert exit status, stdout, stderr, and changed files.
- Cover invalid input, a missing dependency, an unsafe path, and failure propagation.
- Work in temp directories. Never touch the real home, git config, cloud, or system state.
- Pin `PATH`, locale, env vars, and working directory so tests are deterministic. Use `PATH` fixtures to stub external commands.
