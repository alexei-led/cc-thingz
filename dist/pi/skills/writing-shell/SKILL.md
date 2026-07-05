---
description: Idiomatic shell development for POSIX sh, Bash, Zsh, Fish, hooks, CI
  shell steps, and scriptable CLI glue. Use when writing or changing `.sh`, `.bash`,
  `.zsh`, `.fish`, `.bats`, shell functions, shell pipelines, CI `run:` shell bodies,
  or command-runner recipes. Emphasizes portability, quoting, safe filesystem/process
  handling, non-TUI CLI tools, ShellCheck, shfmt, Bats, and ShellSpec. NOT for Python,
  Rust, TypeScript, Go, web code, or GitHub Actions workflow/job/permissions semantics;
  use operating-infra.
name: writing-shell
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, subagent, wait, web_search, web_answer, web_research. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Shell Development

## Scope

- Use for shell scripts, hooks, CI shell blocks, command pipelines, and local automation glue.
- In GitHub Actions, own the shell code inside `run:` blocks. Use
  `operating-infra` for workflow YAML structure, jobs, permissions, runners,
  actions, secrets, caching, concurrency, and policy. Mixed changes compose both
  skills.
- Do not use for cloud, Kubernetes, Terraform, host, or network operations; use `operating-infra`.
- Do not use for application logic that belongs in Python, Rust, Go, TypeScript, or another project language.

## Read references

- Read [patterns.md](references/patterns.md) before non-trivial scripts or pipelines.
- Read [tools.md](references/tools.md) when choosing external CLI tools or parsing structured data.
- Read [testing.md](references/testing.md) before adding or changing shell tests or quality gates.

## Defaults

- Follow the existing shebang, shell, style, and project tooling first.
- For new portable scripts, use POSIX `sh` when the logic is simple; use Bash when arrays, `pipefail`, regex, or richer functions are needed.
- Use Zsh or Fish only for existing files or explicit user intent. Keep Fish/Zsh config separate from portable scripts.
- Do not rely on the agent's current shell. Put the intended shell in the shebang or invoke it explicitly in tests.
- Prefer small shell scripts that call stable tools. Move complex data modeling or business logic to a real language.

## Core rules

- Quote expansions unless word splitting is intentional and documented by structure.
- Avoid `eval`, `curl | sh`, parsing `ls`, unguarded globbing, and unsafe `rm`/`mv`/`cp` paths.
- Use arrays for arguments in Bash; use newline/NUL-safe loops for filenames.
- Use `mktemp` plus cleanup traps for temporary files and directories.
- Check required external commands when a script depends on them. Do not install tools silently.
- Account for macOS/BSD versus GNU flag differences when writing portable scripts.
- Prefer machine-readable output from tools, then parse it with structured parsers.
- Use `looking-up-docs` for exact external CLI flags, syntax, or version behavior; do not guess from memory.

## Comments

- Comment only tricky, non-obvious, important, or unusual shell behavior.
- Use file and function comments for reusable scripts or functions when the contract is not obvious from names and usage.
- Add a short reason after any `shellcheck disable` directive.
- Keep comments short. Move longer rationale to docs, issue links, or design notes.
- Do not comment obvious commands or narrate each pipeline stage.
- Keep shell tests readable without comments; add one only for unobvious fixtures, environment setup, portability constraints, or regression context.

## Verification

Run the project-configured shell gates. Prefer:

- formatting: `shfmt`
- linting: `shellcheck`; `checkbashisms` for POSIX `sh`
- tests: Bats for Bash-heavy projects; ShellSpec for POSIX or multi-shell behavior
- security/policy: Semgrep shell rules when the script handles secrets, downloads, deletion, or user-controlled input

If a tool is unavailable or unconfigured, state the gap and run the closest available check. If a check fails, quote the diagnostic, fix the cause, and rerun the relevant check.

## Final response

Include:

- changed files
- shell target used: POSIX sh, Bash, Zsh, or Fish
- checks run and results
- checks skipped with reasons
- remaining portability or safety risks
