# Shell Testing and Quality Gates

## Tool selection

- `shfmt`: formatter and format check for shell scripts.
- `shellcheck`: primary static analyzer for POSIX sh and Bash; use the correct shebang or shell option.
- `checkbashisms`: POSIX portability check for `/bin/sh` scripts.
- Bats: prefer for Bash-heavy projects when already configured or cheap to add.
- ShellSpec: prefer for POSIX or multi-shell behavior tests.
- Semgrep: use shell/security rules for scripts that handle secrets, downloads, deletion, permissions, or user-controlled input.
- `bashate`: run only when the project already uses it.
- `shellharden`: use only with tests and diff review because rewrites can change behavior.

## Test design

- Test behavior through the script entrypoint, not private helper internals.
- Cover success, invalid input, missing dependency, unsafe path, and failure propagation.
- Use temporary directories and fixtures; do not touch real home, cloud, git, or system state.
- Assert exit status, stdout, stderr, and changed files when relevant.
- Keep tests deterministic: set env vars, locale-sensitive values, PATH fixtures, and working directory explicitly.
- Test the intended shell explicitly instead of relying on the runner's login shell.

## Verification flow

1. Format or check formatting.
2. Run static analysis.
3. Run portability checks when the script claims POSIX compatibility.
4. Run shell tests.
5. Run security/policy scans for risky scripts.

Report skipped gates with the reason: tool missing, no test suite, no POSIX target, or outside task scope.
