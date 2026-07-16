# cc-thingz — Coding Companion

[![CI](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml/badge.svg)](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent Bundler](https://img.shields.io/badge/Agent_Bundler-v0.4.2+-00897B)](https://github.com/alexei-led/agentbundler)
[![Skills](https://img.shields.io/badge/skills-29-green)](src/skills/)

Portable skills and agents for Claude Code, Codex CLI, Pi, GitHub Copilot, and
Cursor, and Grok. Gemini is retired.

## Build

Install Agent Bundler v0.4.2 or newer:

```bash
brew install alexei-led/tap/agentbundler
agbun --version
```

Build and check the complete generated tree:

```bash
make build
make check
```

`make build` is a direct `agbun build --root .` invocation. `make check` runs
the build and then `agbun check --root .`. Agent Bundler replaces the configured
`dist/` output tree, so do not edit generated files.

## Source layout

```text
agentbundle.json                    # Agent Bundler manifest
src/
├── skills/<name>/SKILL.md          # canonical YAML-frontmatter skills
│   └── .agentbundler/targets/*.json # optional target overlays
├── agents/<name>.md                # canonical agent assets
├── .agentbundler/packages/*.json   # package membership and metadata
├── hooks/<name>/                   # typed Agent Bundler hooks
└── pi-extensions/                  # source-only Pi-native extension gap

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

## Installation boundaries

Agent Bundler renders package layouts. It does not publish marketplaces, install
packages, run vendor smoke tests, or package arbitrary Pi-native extensions.

The generated package roots are intended to be copied or installed according to
the target vendor's current documentation. No cc-thingz marketplace manifest
is generated anymore.

Agent Bundler v0.4.2 emits typed hook payloads and manifests, including the Pi
aggregate hook runtime. The source-only Pi extensions in `src/pi-extensions/`
remain unbundled because arbitrary Pi native resources are not yet supported.

## Agent Bundler gaps

Current `agbun v0.4.2` still does not provide these cc-thingz behaviors:

- Pi TypeScript extension copying and runtime package registration;
- typed Claude lifecycle hooks for exit-plan mode and worktree creation/removal;
- portable blocking/rewrite hooks outside Pi;
- a lossless Cursor edit matcher or Pi notification event;
- marketplace publishing, installation workflows, or vendor runtime smoke tests.

See [Agent Bundler gaps](docs/agentbundler-gaps.md) for the exact capability
requests and source-only compatibility hooks.

These gaps are now explicit. Add a native adapter only when the behavior is
needed; do not rebuild a second general-purpose skill compiler in Python.

## Development checks

```bash
make lint
make validate
make build
make check
make test
make test-ts
make ci
```

`make validate` checks Agent Bundler availability, source genericity, and
executable source scripts. `make test` covers source and release helpers.
`make test-ts` covers source-only Pi extension behavior. `make test` verifies
Agent Bundler hook manifests and Pi decision-hook protocol output.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Keep canonical content under `src/`,
package configuration in `agentbundle.json` and `src/.agentbundler/packages/`,
and generated output under `dist/`.

## License

[MIT](LICENSE)
