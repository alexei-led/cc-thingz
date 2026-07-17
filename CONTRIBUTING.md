# Contributing

## Source of truth

`src/` and the root `agentbundle.json` are the hand-authored build inputs.
An installed compatible Agent Bundler build renders and packages the active
targets; see [Agent Bundler migration status](docs/agentbundler-gaps.md).

```text
src/
├── skills/<name>/SKILL.md          # YAML frontmatter + support files
│   └── .agentbundler/targets/*.json # optional Agent Bundler overlays
├── agents/<name>.md                # portable agent assets
├── .agentbundler/packages/*.json   # package membership and metadata
├── hooks/<name>/                   # typed Agent Bundler hook assets
├── plugins/pi/<asset>/             # declarative Pi-native extension trees
└── pi-extensions/                  # source-only legacy extension dependencies

agentbundle.json                    # Agent Bundler manifest
 dist/                              # generated; do not edit
```

Gemini is retired. Do not add Gemini targets, overlays, manifests, symlinks, or
installation documentation.

## Prerequisites

```bash
uv sync --all-groups
bun install
agbun package --help # must support deterministic target archives
```

## Build and validation

```bash
make build     # agbun build --root .
make check     # non-mutating agbun check --root .
make validate  # Agent Bundler version, genericity, executable checks
make test      # pytest
make test-ts   # Pi extension tests, including generated native-extension sources
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

Packages render under `dist/<target>/<package-id>/`; Codex project agents render
separately at `dist/codex/.codex/agents/*.toml`. Package metadata and membership
come from `src/.agentbundler/packages/*.json`. Add an asset to a package JSON
only when it is canonical source; do not edit generated output.

## Overlays

Add target differences beside the asset:

```text
src/skills/example/.agentbundler/targets/pi.json
src/agents/reviewer.md.agentbundler/targets/claude.json
```

Use Agent Bundler's JSON sidecar fields: `frontmatterPatch`, `bodyPatch`,
`files`, and `deletedFiles`. Use a composition entry in `agentbundle.json` for
target-wide `skillPreamble`.

Canonical skill frontmatter remains YAML. Agent Bundler accepts it and emits
normalized JSON. Keep values JSON-compatible.

## Known Agent Bundler gaps

The current compatible Agent Bundler tree renders typed hooks, per-agent
sidecars, bundled Pi dependencies, target catalogs, and deterministic release
archives. It does not yet render:

- complete legacy Pi hook-runner configuration;
- Claude lifecycle hooks for exit-plan mode or worktree creation/removal;
- portable blocking/rewrite hooks outside Pi;
- a lossless Cursor edit matcher or Pi notification event;
- complete vendor runtime smoke tests.

`src/hooks/UNSUPPORTED.md` lists source-only lifecycle hooks excluded from all
packages. Pi-native extension trees live under `src/plugins/pi/<asset>/` and
need an `.agentbundler/asset.json` that explicitly lists registered
`piExtensions`. `src/pi-extensions/` retains only the incomplete legacy
hook-runner, permission-gate, plan-mode, and shared bridge. Do not add a custom
compiler or post-build copier.

## Git hooks and CI

`make setup` installs the repository hooks. Pre-commit runs lint/validation and
rebuilds when `src/` or `agentbundle.json` changes. Pre-push runs `make check`,
Python tests, and TypeScript tests. CI installs the pinned Agent Bundler release
before `make validate`, `make check`, and tests.

## Releases

Release notes derive package descriptions from `src/.agentbundler/packages/`.
The release workflow runs Agent Bundler before creating a release. There is no
marketplace-generation step in this pipeline.
