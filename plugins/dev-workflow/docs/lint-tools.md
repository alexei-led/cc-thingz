# smart-lint.sh — tools, configuration, skip recipes

`smart-lint.sh` is a `PostToolUse` hook that runs after every Write/Edit/MultiEdit. It auto-detects project languages and runs whatever formatters and linters are installed. Tools are **optional**: missing tools are quietly skipped, present tools are used.

## Fast tier — style, syntax, types

These run on changed files. Install only what you want; the script no-ops on missing binaries.

| Tool            | Languages                          | Install                                                             |
| --------------- | ---------------------------------- | ------------------------------------------------------------------- |
| `gofmt`         | Go                                 | bundled with `brew install go`                                      |
| `golangci-lint` | Go                                 | `brew install golangci-lint`                                        |
| `ruff`          | Python                             | `uv tool install ruff` _(or `brew install ruff`)_                   |
| `pyright`       | Python                             | `uv tool install pyright` _(or `bun add -g pyright`)_               |
| `prettier`      | JS, TS, JSON, MD                   | `bun add -g prettier` _(or `npm i -g prettier`)_                    |
| `eslint`        | JS, TS                             | already invoked through `npm run lint` if `package.json` defines it |
| `yq`            | YAML                               | `brew install yq`                                                   |
| `yamllint`      | YAML                               | `uv tool install yamllint` _(or `brew install yamllint`)_           |
| `jq`            | JSON                               | `brew install jq`                                                   |
| `shellcheck`    | shell                              | `brew install shellcheck`                                           |
| `shfmt`         | shell                              | `brew install shfmt`                                                |
| `actionlint`    | GitHub Actions                     | `brew install actionlint`                                           |
| `terraform`     | Terraform                          | `brew install terraform`                                            |
| `tflint`        | Terraform                          | `brew install tflint`                                               |
| `markdownlint`  | Markdown                           | `bun add -g markdownlint-cli`                                       |
| `mdformat`      | Markdown (fallback if no prettier) | `uv tool install mdformat`                                          |

## Architecture tier — boundaries, dead code

These run **only when their config file is present**. No env var to enable; the config file is the opt-in. Skipped entirely with `SKIP_ARCH=1` or `.nolint-arch`.

### Knip — unused exports / files / deps (TypeScript, JavaScript)

- **Install**: `bun add -g knip` _(or `npm i -g knip`)_
- **Trigger**: any of `knip.json`, `knip.jsonc`, `knip.ts`, `knip.js` in the project root.
- **Docs**: <https://knip.dev/>
- **Caveat**: knip runs project-wide. The hook only invokes it when a `.js`/`.ts`/`.jsx`/`.tsx` file changed in the same edit batch — if you only change `package.json` (e.g., adding a dep), run `knip` manually.

Minimal `knip.json`:

```json
{
  "$schema": "https://unpkg.com/knip@5/schema.json",
  "entry": ["src/index.ts"],
  "project": ["src/**/*.ts"]
}
```

### dependency-cruiser — module boundaries and import cycles (TypeScript, JavaScript)

- **Install**: `bun add -g dependency-cruiser` _(or `npm i -g dependency-cruiser`)_. CLI binary is `depcruise`.
- **Trigger**: any of `.dependency-cruiser.cjs`, `.dependency-cruiser.js`, `.dependency-cruiser.json`, `.dependency-cruiser.mjs`.
- **Docs**: <https://github.com/sverweij/dependency-cruiser>
- **Target**: hook validates `src/` if it exists, else `.`.

Generate a starter config: `depcruise --init`. The default `forbidden` rules already catch cycles and orphans.

### Go architecture — use `golangci-lint`, not a separate tool

Go architecture/boundary enforcement lives inside `golangci-lint`, which the hook already runs. Configure it via `.golangci.yml`:

```yaml
linters:
  enable:
    - depguard # package import allow/deny
    - gomodguard # module-level allow/deny
    - cyclop # cyclomatic complexity
    - revive # configurable rules incl. cognitive-complexity
    - gocyclo # complexity
    - gocognit # cognitive complexity

linters-settings:
  depguard:
    rules:
      domain-pure:
        files: ["**/internal/domain/**"]
        deny:
          - pkg: database/sql
            desc: "domain layer must not depend on a database driver"
```

`golangci-lint` docs: <https://golangci-lint.run/>

## Skip recipes

| Goal                                                   | Mechanism                                                                                                                                     |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Skip all linting once                                  | `SKIP_LINT=1` in the environment                                                                                                              |
| Skip all linting persistently                          | `touch .nolint` in project root (add to `.gitignore`)                                                                                         |
| Skip just the slow architecture tier (knip, depcruise) | `SKIP_ARCH=1` or `touch .nolint-arch`                                                                                                         |
| Skip a specific tool                                   | uninstall it, or use the tool's own ignore mechanism (`.knipignore`, depcruise `excludeOnly`, `// eslint-disable-line`, `# noqa`, `//nolint`) |

There is no `SKIP_LANG` or `SKIP_TOOL` env var. The set above is enough in practice; finer granularity will be added if a real need shows up.

## Layered hook config

`smart-lint.sh` sources two optional shell files in order:

1. `~/.claude/.claude-hooks-config.sh` — global defaults
2. `./.claude-hooks-config.sh` — project overrides (project file wins because it's sourced last)

Use these to set hook-level switches (debug output, `SKIP_LINT`, future toggles). The per-tool linters (`golangci-lint`, `ruff`, `prettier`, etc.) read their **own** project configs (`.golangci.yml`, `pyproject.toml`, `.prettierrc`); those are the natural place to control tool behavior.

Example global default:

```bash
# ~/.claude/.claude-hooks-config.sh
export CLAUDE_HOOKS_DEBUG=0
```

Example project override:

```bash
# ./.claude-hooks-config.sh
export CLAUDE_HOOKS_DEBUG=1   # this project: verbose lint output
export SKIP_ARCH=1            # this project: knip/depcruise off for now
```

## How errors reach the model

When a tool fails, the hook prints to stderr and exits `2`. Claude Code feeds the stderr back to the model so it can fix the issue without a second prompt. Install hints (missing binary but config file present) go to stdout instead, so they do not block the edit and do not get treated as work.

## Out of scope (deliberate)

- Go: `go-arch-lint`, `nilaway` — niche / narrow adoption. Use `depguard` via golangci-lint.
- Python: `import-linter`, `deptry`, `vulture`, `xenon` — small adoption signals. `ruff` covers complexity (`C90`, `PLR`) and tidy-imports (`TID`); `pyright` covers types.
- Cross-language: `semgrep`, `ast-grep` — semgrep skews security; ast-grep too new.

If a tool here grows clear adoption, wire it up the same way: opt-in by config-file presence, no new env var.
