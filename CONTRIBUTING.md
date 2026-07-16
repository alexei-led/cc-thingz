# Contributing

## Source of truth

`src/` and the root `agentbundle.json` are the hand-authored build inputs.
Agent Bundler v0.4.2+ renders the active package targets.

```text
src/
├── skills/<name>/SKILL.md          # YAML frontmatter + support files
│   └── .agentbundler/targets/*.json # optional Agent Bundler overlays
├── agents/<name>.md                # portable agent assets
├── .agentbundler/packages/*.json   # package membership and metadata
├── hooks/<name>/                   # typed Agent Bundler hook assets
└── pi-extensions/                  # source-only Pi-native extension gap

agentbundle.json                    # Agent Bundler manifest
 dist/                              # generated; do not edit
```

Gemini is retired. Do not add Gemini targets, overlays, manifests, symlinks, or
installation documentation.

## Prerequisites

```bash
uv sync --all-groups
bun install
brew install alexei-led/tap/agentbundler
agbun --version # v0.4.2 or later
```

## Build and validation

```bash
make build     # agbun build --root .
make check     # rebuild, then agbun check --root .
make validate  # Agent Bundler version, genericity, executable checks
make test      # pytest
make test-ts   # Pi extension tests; native extensions are not bundled by agbun
make ci        # all local gates
```

`agbun build` owns the complete `dist/` tree. Its output directory is not a
staging area: the command replaces it. Keep the manifest output dedicated.
`agbun check` is the generated-drift gate and exits 2 when output is missing,
changed, extra, non-regular, or symlinked.

## Agent Bundler targets

Active targets in `agentbundle.json`:

- Claude Code
- Codex
- Pi
- GitHub Copilot
- Cursor
- Grok

The generated target roots are `dist/<target>/<package-id>/`. Package metadata
and membership come from `src/.agentbundler/packages/*.json`. Add an asset to a
package JSON only when it is canonical source; do not edit generated output.

## Overlays

Add target differences beside the asset:

```text
src/skills/example/.agentbundler/targets/pi.json
```

Use Agent Bundler's JSON sidecar fields: `frontmatterPatch`, `bodyPatch`,
`files`, and `deletedFiles`. Use a composition entry in `agentbundle.json` for
target-wide `skillPreamble`.

Canonical skill frontmatter remains YAML. Agent Bundler accepts it and emits
normalized JSON. Keep values JSON-compatible.

## Known Agent Bundler gaps

Agent Bundler v0.4.2 renders typed hooks, payloads, target manifests, and the
Pi aggregate hook runtime. It does not yet render:

- Pi TypeScript extensions or arbitrary Pi native-resource registration;
- Claude lifecycle hooks for exit-plan mode or worktree creation/removal;
- portable blocking/rewrite hooks outside Pi;
- a lossless Cursor edit matcher or Pi notification event;
- repository marketplace publishing, installation workflows, or vendor runtime
  smoke tests.

`src/hooks/UNSUPPORTED.md` lists source-only lifecycle hooks excluded from all
packages. `src/pi-extensions/` remains source-only until Agent Bundler gains a
Pi native-resource registration contract. Do not add a custom compiler.

## Git hooks and CI

`make setup` installs the repository hooks. Pre-commit runs lint/validation and
rebuilds when `src/` or `agentbundle.json` changes. Pre-push runs `make check`,
Python tests, and TypeScript tests. CI installs the pinned Agent Bundler release
before `make validate`, `make check`, and tests.

## Releases

Release notes derive package descriptions from `src/.agentbundler/packages/`.
The release workflow runs Agent Bundler before creating a release. There is no
marketplace-generation step in this pipeline.
