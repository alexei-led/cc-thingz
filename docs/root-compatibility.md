# Repository-root compatibility

cc-thingz is authored once and compiled into native target roots under
`dist/<target>`. The repository root also contains small compatibility manifests
so existing local-path and Git installations can find those generated roots.

The compatibility layer contains no copied skill trees and uses no symlinks.
Each marketplace entry points to its target package under `dist/`. Pi is the
exception: its fields are merged into the development `package.json` because Pi
only reads `package.json#pi` from the installed package root.

## Root contract

- `.claude-plugin/marketplace.json` points to `dist/claude/<package>`.
- `.agents/plugins/marketplace.json` points to `dist/codex/<package>`.
- `.codex/agents/*.toml` mirrors `dist/codex/.codex/agents/*.toml` because Codex
  discovers project-agent profiles by fixed path rather than marketplace source.
- `.github/plugin/marketplace.json` points to `dist/copilot/<package>`.
- `.cursor-plugin/marketplace.json` points to `dist/cursor/<package>`.
- `package.json#pi` points to `dist/pi/{extensions,skills,agents}`.
- Root `package.json` depends on `pi-subagents`; Pi installs that dependency when
  it clones a Git package and loads its extension from root `node_modules`.
- Root `.npmrc` sets `legacy-peer-deps=true` so that production Git installs do
  not auto-install the Pi host packages declared as development peers.

All relative paths must stay inside the repository and resolve to existing
package roots. `tests/test_root_compatibility.py` compares each wrapper with its
canonical generated target manifest and checks every resolved plugin manifest.

## Installation

### Claude Code

```bash
claude plugin marketplace add alexei-led/cc-thingz
claude plugin list --available --json
```

For a checkout under development:

```bash
claude plugin marketplace add "$PWD"
```

Adding a marketplace exposes its packages; it does not install all seven. Use
`/plugin` or install the required IDs as `<package>@cc-thingz`.

### Codex CLI

```bash
codex plugin marketplace add alexei-led/cc-thingz
codex plugin list --json
```

For a checkout under development:

```bash
codex plugin marketplace add "$PWD" --json
```

Install the required package IDs from the registered `cc-thingz` marketplace.
Codex project-agent profiles are a separate contract. The repository mirrors
the generated profiles into root `.codex/agents`, so Codex discovers them when
running in this checkout. Marketplace plugin installation covers plugin
packages, not project profiles in the marketplace cache; install the profiles
through Codex's project/user agent mechanism when using cc-thingz outside this
checkout.

### Pi

```bash
pi install git:github.com/alexei-led/cc-thingz
```

For a built checkout under development:

```bash
bun install
make build
pi install "$PWD"
```

Restart Pi or run `/reload`, then verify that `cc-thingz.*` subagents and a
cc-thingz skill such as `fixing-code` are present. `pi list` alone proves package
registration, not resource loading.

Git installation is intentionally different from installing `dist/pi`: Pi
clones the root, installs root production dependencies, and then resolves the
prefixed `dist/pi` resources. `.npmrc` suppresses automatic installation of host
peer packages while preserving `pi-subagents` and its required nested runtime.
A clean local checkout must run `bun install` so root
`node_modules/pi-subagents` exists.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add alexei-led/cc-thingz
copilot plugin marketplace browse cc-thingz
```

For a checkout under development:

```bash
copilot plugin marketplace add "$PWD"
```

Install the required package IDs as `<package>@cc-thingz`, then verify them with
`copilot plugin list`.

### Cursor

The root `.cursor-plugin/marketplace.json` uses Cursor's native marketplace
schema and points to `dist/cursor/<package>`. Register or publish the repository
through Cursor Marketplace, or test the generated target through Cursor's local
plugin directory. The current Cursor CLI has no plugin-management command, so
CI validates the manifest and resolved plugin roots; a full runtime smoke needs
Cursor Marketplace state and credentials.

### Grok

Grok reads Claude Code marketplace manifests for compatibility. Therefore the
repository-root `.claude-plugin/marketplace.json` registers the Claude-compatible
cc-thingz packages:

```bash
grok plugin marketplace add alexei-led/cc-thingz
grok plugin list --available --json
```

For Grok-specific overlays and hook scripts, use the native generated target:

```bash
grok plugin marketplace add "$PWD/dist/grok"
```

Claude and Grok use the same root marker, but their generated package content is
not identical. One `.claude-plugin/marketplace.json` cannot conditionally route
Claude to `dist/claude` and Grok to `dist/grok`. Root installation therefore
uses Claude-compatible content; `dist/grok` remains the authoritative
Grok-specific package root.

## Verification coverage

`tests/test_root_compatibility.py` checks:

- root marketplace parity and prefixed paths for Claude, Codex, Copilot, and
  Cursor;
- all referenced plugin manifests exist;
- root Codex project-agent profiles byte-match the generated profiles;
- root production npm installation excludes Pi host peers while keeping the
  `pi-subagents` runtime;
- root Pi fields preserve the development package and resolve every resource;
- isolated local marketplace registration for installed Claude, Codex, Copilot,
  and Grok CLIs;
- isolated Pi local installation followed by RPC command discovery;
- a real Git-over-HTTP Pi installation, including dependency installation and
  RPC discovery of extensions, skills, and the `pi-subagents` runtime.

Vendor CLI checks skip when a CLI is unavailable. Cursor runtime loading remains
credential- and marketplace-dependent.

## Ownership

The target manifests under `dist/` are canonical. Agent Bundler generates the
root wrappers from `agentbundle.json#compatibility.rootManifests` and owns the
compatibility state. Root files must not acquire independent package metadata.
`agbun build` updates them; `agbun check` reports wrapper drift without rewriting
files.
