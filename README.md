# cc-thingz — Coding Companion

[![CI](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml/badge.svg)](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Targets](https://img.shields.io/badge/targets-6-00897B)](agentbundle.json)
[![Skills](https://img.shields.io/badge/skills-29-green)](src/skills/)
[![Agent Bundler](https://img.shields.io/badge/Agent_Bundler-required-00897B)](https://github.com/alexei-led/agentbundler)

Portable skills, agents, hooks, and Pi-native extensions for Claude Code, Codex
CLI, GitHub Copilot, Cursor, Grok, and Pi. Gemini is retired.

## Build

Requires Agent Bundler with `build`, `check`, and `package`, plus support for
per-agent sidecars, declared hook environments, Pi-native assets, and Codex
project-agent profiles. Verify packaging support:

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
└── plugins/pi/<asset>/             # declarative Pi-native extension tree
    └── extensions/                 # Pi-native tools and compatibility runner

dist/<target>/<package>/             # generated Agent Bundler package roots
.claude-plugin/marketplace.json      # repository-root compatibility wrapper
.agents/plugins/marketplace.json     # repository-root compatibility wrapper
.codex/agents/*.toml                 # fixed-path Codex project-agent profiles
.github/plugin/marketplace.json      # repository-root compatibility wrapper
.cursor-plugin/marketplace.json      # repository-root compatibility wrapper
package.json#pi                      # merged Pi root compatibility manifest
```

Skills use Agent Bundler overlays for target-specific frontmatter, body, and
support-file changes. Target-wide preambles are composition entries in
`agentbundle.json`. Canonical source remains readable Markdown with YAML
frontmatter; Agent Bundler emits normalized JSON frontmatter.

Package membership is defined by `src/.agentbundler/packages/*.json`. Each
package lists exact skill and agent asset paths. Root marketplace files are
routing wrappers only: their entries point into `dist/<target>` and contain no
independent package trees. Do not edit `dist/` or give the wrappers independent
metadata.

## Targets and output

| Target         | Output                    | Package contract                                      |
| -------------- | ------------------------- | ----------------------------------------------------- |
| Claude Code    | `dist/claude/<package>/`  | Marketplace packages, agents, and hooks               |
| Codex CLI      | `dist/codex/<package>/`   | Plugin packages plus `.codex/agents/*.toml` profiles  |
| Pi             | `dist/pi/`                | Aggregate package, typed hooks, and native extensions |
| GitHub Copilot | `dist/copilot/<package>/` | Marketplace packages, agents, and hooks               |
| Cursor         | `dist/cursor/<package>/`  | Marketplace packages, agents, and supported hooks     |
| Grok Build     | `dist/grok/<package>/`    | Marketplace packages, agents, and hooks               |
| Gemini CLI     | none                      | Retired                                               |

## Release packages

`agbun package --root . --out DIR` creates deterministic, target-native release
archives:

- `cc-thingz-claude.tar.gz`
- `cc-thingz-codex.tar.gz`
- `cc-thingz-pi.tgz`
- `cc-thingz-copilot.tar.gz`
- `cc-thingz-cursor.tar.gz`
- `cc-thingz-grok.tar.gz`

The release workflow attaches all six files. Each archive expands directly to
the native package or marketplace root shown above. The Codex archive also
includes separate `.codex/agents/*.toml` profiles; they are not plugin contents.
Installation and marketplace registration use the target vendor's CLI; Agent
Bundler does not mutate user configuration or publish to a vendor registry.

## Repository-root installation

Compatibility manifests at the repository root preserve Git and local-path
installation while keeping `dist/<target>` canonical:

```bash
claude plugin marketplace add alexei-led/cc-thingz
codex plugin marketplace add alexei-led/cc-thingz
copilot plugin marketplace add alexei-led/cc-thingz
grok plugin marketplace add alexei-led/cc-thingz
pi install git:github.com/alexei-led/cc-thingz
```

Marketplace registration exposes the seven cc-thingz packages; install the
required package IDs separately. Pi loads the aggregate package. Cursor uses
the root `.cursor-plugin/marketplace.json` through Cursor Marketplace rather
than a plugin-management CLI.

Grok reads the Claude root marketplace for compatibility. Use `dist/grok` for
Grok-specific overlays because Claude and Grok share the same root marker and
cannot both select different target paths from one manifest. Root
`.codex/agents` mirrors the generated project-agent profiles for checkout use;
marketplace plugin installation does not install those fixed-path profiles into
an unrelated Codex project.

See [Repository-root compatibility](docs/root-compatibility.md) for local paths,
verification, limitations, and migration details.

The Pi archive is directly installable:

```bash
pi install ./cc-thingz-pi.tgz -l
```

For a local release rehearsal, build first so the ignored Pi runtime dependencies
exist before packaging:

```bash
agbun build --root .
agbun check --root .
agbun package --root . --out /tmp/cc-thingz-release
```

The generated Pi package includes its typed hook adapter, bundled
`pi-subagents` runtime, native `ask_user_question`, `structured_output`, and
`todo` tools, plus `hook-runner`, `permission-gate`, and `plan-mode`. Its
compatibility config contains only Pi-specific revdiff plan review and
notifications, so portable Agent Bundler hooks do not run twice.

The package command, flat per-agent sidecars, safe Pi hook environments, and
bundled Pi dependencies, native extension assets, and Codex project-agent
profiles require a compatible installed Agent Bundler.

## Target differences and gaps

See [Agent Bundler port status](docs/agentbundler-gaps.md) for target-specific
behavior, runtime validation, and upstream/vendor boundaries. Do not recreate a
custom compiler or post-process `dist/`.

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
executable source scripts. `make test` verifies source/release helpers, hook
manifests, target inventories, agent envelopes, version consistency, archives,
and Pi decision-hook protocol output. `make test-ts` covers Pi-native extension
and compatibility-runner behavior.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Keep canonical content under `src/`,
package configuration in `agentbundle.json` and `src/.agentbundler/packages/`,
and generated output under `dist/`.

## License

[MIT](LICENSE)
