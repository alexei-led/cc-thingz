# Scriptable CLI Tools

Use non-interactive, pipe-friendly tools with stable stdout and useful exit codes. Avoid TUI, color, paging, prompts, and progress output when another command consumes stdout.

## Rules

- Prefer installed project tools over introducing new dependencies.
- If a script depends on a non-standard tool, check for it and fail with a clear message.
- Do not silently install missing tools.
- Use JSON, YAML, CSV, TOML, or XML parser output over text scraping.
- Keep macOS/Linux portability in mind; document GNU-only requirements when unavoidable.
- Route cloud, Kubernetes, Terraform, host, network, Docker, secrets,
  supply-chain policy, and GitHub Actions workflow/job/permissions semantics to
  `operating-infra`; keep shell code inside `run:` blocks here.

## Common choices

- Search and discovery: `rg`, `fd`
- Text replacement preview: `sd -p`
- Structured data: `jq`, `yq`, `dasel`, `mlr`, `xsv`, `jo`
- HTTP/API checks: `curl`, `xh`, or `httpie` only for local script glue
- File-change reruns: `watchexec`, `entr`
- Benchmarks/progress: `hyperfine`, `pv`
- Batched execution: `parallel`, `xargs`
- Project runners: existing `make`, `just`, or `task`
