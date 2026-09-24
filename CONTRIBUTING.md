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
    └── extensions/                 # Pi-native tools and compatibility runner

agentbundle.json                    # Agent Bundler manifest
 dist/                              # generated; do not edit
```

Gemini is retired. Do not add Gemini targets, overlays, manifests, symlinks, or
installation documentation.

## Prerequisites

```bash
uv sync --all-groups
bun install --frozen-lockfile
scripts/setup/install-agbun.sh
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

Repository-root marketplace files and `package.json#pi` are compatibility
wrappers around those target trees. Agent Bundler renders them from
`agentbundle.json#compatibility.rootManifests`; they may only prefix generated
local sources with `dist/<target>` and must not define independent package
membership or copy generated trees. Codex is the fixed-path exception: root
`.codex/agents/*.toml` must byte-match the generated project-agent profiles.
`tests/test_root_compatibility.py` verifies the generated routing contract.

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

- Claude lifecycle hooks for worktree creation/removal;
- Codex agent model and reasoning-effort fields;
- a lossless Cursor edit matcher;
- portable Pi notification mapping;
- complete vendor runtime smoke tests.

`src/hooks/UNSUPPORTED.md` lists source-only lifecycle hooks excluded from all
packages. Pi-native extension trees live under `src/plugins/pi/<asset>/` and
need an `.agentbundler/asset.json` that explicitly lists registered
`piExtensions`. The extension tree also contains unregistered support modules,
Pi-specific compatibility hooks, and revdiff's wrapper. Do not add a custom
compiler or post-build copier.

## Git hooks and CI

`make setup` installs the repository hooks. Pre-commit runs lint/validation and
rebuilds when `src/` or `agentbundle.json` changes. Pre-push runs `make lint`,
`make check`, Python tests, and TypeScript tests. CI installs the pinned Agent Bundler release
from `.agentbundler-version` before `make validate`, `make check`, and tests.
The separate scheduled canary checks upstream latest without changing the release
pin. Core runtime smoke dependencies live in `tests/vendor-smoke/package-lock.json`;
update them deliberately and rerun the isolated installation tests.

## Releases

The version section in `CHANGELOG.md` is the single authored source for release
notes. Validate it with the packaged checker, for example:

```bash
python3 src/skills/releasing-code/scripts/release_notes.py check-release \
  --root . --tag v6.13.0 --changelog CHANGELOG.md --budget minor
```

Prepare with `scripts/release/release-tag prepare vX.Y.Z` or
`make release V=X.Y.Z`. Preparation updates version metadata, generated output,
and a blank version section; it does not commit, tag, or push. Write and review the notes,
then commit all release changes. Run
`scripts/release/release-tag finalize vX.Y.Z` or
`make release-finalize V=X.Y.Z` on that clean commit. Finalization validates the
notes and version identity, runs `make ci`, and creates a local annotated tag; it
does not push. It rejects an existing local or remote tag and never moves one.

The tag-triggered `.github/workflows/release.yml` is the only GitHub release
publisher for cc-thingz. It validates tag, package-version identity, and notes
before packaging or publication. Its manual `workflow_dispatch` path requires
the existing tag plus an explicit full `notes_source_sha` commit. It reads only
`CHANGELOG.md` from that commit and uses manifests from the tagged release. It
rejects draft and prerelease targets, verifies tag/version and six expected
assets, stores the prior title/body and publication-state flags in a 90-day
workflow artifact linked in the run summary, and permits correction of a wrong
title before verifying the exact tag title, notes, and published state. It
uploads no package files during repair. Do not use
`gh release create` or `gh release edit` for cc-thingz. The optional `HOOK_RELEASE_GUARD=1` check covers only direct supported
`gh release` forms; it is not authorization and does not parse general shell or
release-policy configuration. External publication still requires explicit
user authorization.
