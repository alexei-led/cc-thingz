---
{"description":"Idiomatic shell development for POSIX sh, Bash, Zsh, Fish, hooks, CI shell steps, and scriptable CLI glue. Use when writing or changing `.sh`, `.bash`, `.zsh`, `.fish`, `.bats`, shell functions, shell pipelines, CI `run:` shell bodies, or command-runner recipes. Emphasizes portability, quoting, safe filesystem/process handling, non-TUI CLI tools, ShellCheck, shfmt, Bats, and ShellSpec. NOT for Python, Rust, TypeScript, Go, web code, or GitHub Actions workflow/job/permissions semantics; use operating-infra.","name":"writing-shell"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for authorized delegation. Ordinary async subagents notify the parent natively; yield instead of polling or calling bg_wait merely because a child is active. Use blocking bg_wait only for provider, detached, or other background work without a native notification when a required same-turn result is needed. -->
<!-- Current pi-subagents uses one model per launch; do not configure fallbackModels. A different model requires an explicit new launch after inspecting the failed run and partial work. Use the owning workflow/controller for retries. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->


# Shell Development

In GitHub Actions, this skill owns the shell inside `run:` blocks; operating-infra owns the workflow YAML around it (jobs, permissions, actions, secrets, caching). Mixed changes use both.

## Shell Choice

- Follow the existing shebang and tooling. New portable scripts: POSIX `sh` for simple logic; Bash when you need arrays, `pipefail`, `[[ ]]`, or regex.
- Zsh and Fish only for existing files, interactive config, or explicit requests.
- Never rely on the agent's own shell. Name the shell in the shebang, and invoke it explicitly in tests.
- Shell is glue. Move data modeling, business logic, or CPU-heavy work to the project's real language.

## Safety and Portability

- Bash: `set -euo pipefail`, knowing it does not fire inside conditionals or `&&`/`||` lists. POSIX sh: `set -eu` and explicit pipeline checks.
- Build commands with arrays, never strings plus `eval`. Put `--` before user-controlled operands.
- NUL- or newline-safe loops for filenames; never parse `ls` or use `for x in $(cmd)`.
- `mktemp` plus a cleanup `trap` for temp files, locks, and partial outputs.
- No `curl | sh`: download, verify, then run.
- Destructive actions list their targets first and require confirmation unless the script runs non-interactively with explicit inputs.
- macOS/BSD vs GNU: avoid `sed -i`, `date -d`, `readlink -f`, and GNU-only `grep` flags unless the dependency is documented. Prefer `printf` to `echo`.
- Every `shellcheck disable` carries a short reason.

## CLI Tools

- Use non-interactive, pipe-friendly tools with stable stdout and exit codes: no TUI, pager, color, or prompts when output is consumed.
- Parse structured data with `jq`, `yq`, `mlr`, or `dasel`, not `grep`/`sed` scraping. Search with `rg` and `fd`.
- Preview replacements before applying them (`sd -p`, `rg --replace`).
- Check for non-standard tools and fail with a clear message. Never install them silently.
- Look up exact flags with looking-up-docs instead of guessing.

## References

- [testing.md](references/testing.md): gate commands (shfmt, ShellCheck, checkbashisms, Bats, ShellSpec) and test design; read when adding tests or choosing checks.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
