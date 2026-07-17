# cc-thingz — Coding Companion

[![CI](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml/badge.svg)](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent Bundler](https://img.shields.io/badge/Agent_Bundler-compatible_build_required-00897B)](https://github.com/alexei-led/agentbundler)
[![Skills](https://img.shields.io/badge/skills-29-green)](src/skills/)

Portable skills and agents for Claude Code, Codex CLI, Pi, GitHub Copilot,
Cursor, and Grok. Gemini is retired.

## Build

This branch requires an Agent Bundler build with `package`, flat per-agent
sidecars, declared hook environments, bundled Pi dependencies, and native Pi
extension assets and Codex project-agent profiles. Verify the installed binary
supports packaging:

```bash
agbun package --help
```

Build and check the complete generated tree:

```bash
make build
make check
```

`make build` is a direct `agbun build --root .` invocation. `make check` runs
the non-mutating `agbun check --root .` drift gate. Agent Bundler replaces the
configured `dist/` output tree during builds, so do not edit generated files.

## Source layout

```text
agentbundle.json                    # Agent Bundler manifest
src/
├── skills/<name>/SKILL.md          # canonical YAML-frontmatter skills
│   └── .agentbundler/targets/*.json # optional target overlays
├── agents/<name>.md                # canonical agent assets
├── .agentbundler/packages/*.json   # package membership and metadata
├── hooks/<name>/                   # typed Agent Bundler hooks
├── plugins/pi/<asset>/             # declarative Pi-native extension trees
└── pi-extensions/                  # source-only legacy extension dependencies

dist/<target>/<package>/             # generated Agent Bundler package roots
```

Skills use Agent Bundler overlays for target-specific frontmatter, body, and
support-file changes. Target-wide preambles are composition entries in
`agentbundle.json`. Canonical source remains readable Markdown with YAML
frontmatter; Agent Bundler emits normalized JSON frontmatter.

Package membership is defined by `src/.agentbundler/packages/*.json`. Each
package lists exact skill and agent asset paths. Do not create a second package
manifest or edit `dist/` by hand.

## Targets and output

| Target         | Output                    | Status                                 |
| -------------- | ------------------------- | -------------------------------------- |
| Claude Code    | `dist/claude/<package>/`  | enabled                                |
| Codex CLI      | `dist/codex/<package>/`   | enabled                                |
| Pi             | `dist/pi/`                | aggregate package + typed hook runtime |
| GitHub Copilot | `dist/copilot/<package>/` | enabled                                |
| Cursor         | `dist/cursor/<package>/`  | enabled                                |
| Grok Build     | `dist/grok/<package>/`    | enabled                                |
| Gemini CLI     | none                      | retired                                |

## Release packages

`agbun package --root . --out DIR` creates deterministic, target-native release
archives:

- `cc-thingz-claude.tar.gz`
- `cc-thingz-codex.tar.gz`
- `cc-thingz-pi.tgz`
- `cc-thingz-copilot.tar.gz`
- `cc-thingz-cursor.tar.gz`
- `cc-thingz-grok.tar.gz`

Once a compatible Agent Bundler tag is pinned, the release workflow attaches
all six files. Each archive expands directly to the native package or
marketplace root shown above. The Codex archive also includes separate
`.codex/agents/*.toml` profiles; they are not plugin contents. Installation and marketplace
registration still use the target vendor's CLI; Agent Bundler does not mutate
user configuration or publish to a vendor registry.

The Pi archive is directly installable:

```bash
pi install ./cc-thingz-pi.tgz -l
```

For a local release rehearsal:

```bash
agbun check --root .
agbun package --root . --out /tmp/cc-thingz-release
```

The generated Pi package includes its typed hook adapter, bundled
`pi-subagents` runtime, and native `ask_user_question`, `structured_output`,
and `todo` extensions from `src/plugins/pi/extensions/`. The legacy
`hook-runner`, `permission-gate`, `plan-mode`, and shared bridge remain
source-only because their synthetic-hook runtime configuration is incomplete.

The package command, flat per-agent sidecars, safe Pi hook environments, and
bundled Pi dependencies, native extension assets, and Codex project-agent
profiles require a compatible installed Agent Bundler.

## Remaining Agent Bundler gaps

Current unsupported behavior includes Claude exit-plan/worktree lifecycle
hooks, incomplete legacy Pi hook-runner configuration, portable block/rewrite
guards outside Pi, lossless Cursor edit matching, and Pi notifications. Codex
agents render as separate `.codex/agents/*.toml` profiles, not plugin contents.

See [Agent Bundler migration status](docs/agentbundler-gaps.md) for exact
boundaries. Do not recreate a custom compiler or post-process `dist/`.

## Development checks

```bash
make lint
make validate
make build
make check
make test
make test-ts
make ci
agbun package --root . --out /tmp/cc-thingz-release
```

`make validate` checks Agent Bundler availability, source genericity, and
executable source scripts. `make test` covers source and release helpers.
`make test-ts` covers source-only Pi extension behavior. `make test` verifies
Agent Bundler hook manifests, target inventories, agent envelopes, version
consistency, release archives, and Pi decision-hook protocol output.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Keep canonical content under `src/`,
package configuration in `agentbundle.json` and `src/.agentbundler/packages/`,
and generated output under `dist/`.

## License

[MIT](LICENSE)
