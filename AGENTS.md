# cc-thingz — Coding Companion

Portable skills, agents, and typed hooks for Pi, Claude Code, Codex CLI, Copilot, Cursor, and Grok. Agent Bundler (`agbun`) renders them from `src/` into per-target packages under `dist/`.

## Build and check

```bash
make build    # render dist/ and root manifests with Agent Bundler
make fmt      # auto-fix Ruff, the configured JS formatter, and shfmt
make check    # fail on generated drift without rewriting dist/
make ci       # lint + validate + check + test + test-ts
```

- `make build`, `make check`, and `make ci` need the sandbox disabled: the uv cache at `~/.cache/uv` is restricted in the Claude Code sandbox.
- `make build` needs the `agbun` version pinned in `.agentbundler-version`; `scripts/setup/install-agbun.sh` installs it.
- Commit regenerated `dist/` and root manifests together with the `src/` change.
- Done means `make fmt` leaves no diff and `make ci` passes.

## Where things live

- `src/skills/<name>/SKILL.md` — vendor-neutral skill body, with `references/` and `scripts/` beside it.
- `src/agents/<name>.md` — vendor-neutral role bodies.
- `src/hooks/<name>/` — typed hook assets; `src/hooks/UNSUPPORTED.md` records per-target boundaries.
- `src/plugins/pi/` — Pi-native extension trees and the Pi compatibility runner.
- `src/.agentbundler/packages/*.json` — package membership and metadata.
- `agentbundle.json` — targets, composition, and per-target `skillPreamble`.
- `dist/` — generated output; never edit it by hand.
- `docs/` — contributor docs: [Agent Bundler gaps](docs/agentbundler-gaps.md), [Pi package](docs/pi-extensions.md), [skill evals](docs/skill-evals.md).
- `tests/` — pytest, Bats, Pi extension tests, and `tests/skill-evals/` eval suites.

Compiled output paths and overlay mechanics are in [CONTRIBUTING.md](CONTRIBUTING.md#overlays).

## Targets and overlays

Skills and hooks render to all six targets unless a `targets:` key or a package JSON `targets` list restricts them. Target differences live in JSON sidecars beside the asset:

- `src/skills/<name>/.agentbundler/targets/<target>.json`
- `src/agents/<name>.md.agentbundler/targets/<target>.json`
- `src/hooks/<name>/.agentbundler/targets/<target>.json`

A skill with no sidecar, such as `releasing-code`, renders the same body everywhere.

`bodyPatch.mode` is `replace` (whole body) or `sections` (replace one existing, unique heading path; a missing path fails the build). To add target-only text, give the base body a short neutral heading and patch it with `sections`. Use `replace` only for a deliberate full fork, and after `make build` confirm the rendered `dist/<target>/<package>/skills/<name>/SKILL.md` still has the base workflow and reference links.

Base `SKILL.md` and `src/agents/*.md` stay vendor-neutral; `make validate` rejects Claude-only tokens there. Put `$ARGUMENTS`, `AskUserQuestion`, `TaskCreate`, and `mcp__*` names in `.agentbundler/targets/claude.json`.

## Agents

Three roles plus a utility lane. A role is a capability envelope plus a reasoning stance; skills supply domain procedure and output format, and each skill's `references/<lang>.md` supplies language detail.

- `engineer` — read, write, execute. The only mutator; applies changes and verifies them. Claude, Pi, and Grok.
- `reviewer` — read-only adversarial evaluator for review, audit, code location, and planning. Claude, Codex, Pi, Copilot, Cursor, and Grok.
- `runner` — read-only utility lane for bounded lookups. Same targets as reviewer.
- `advisor` — read-only verdict, ranked risks, next actions. Codex and Pi only; Claude Code has a built-in advisor.

Envelope enforcement differs by target:

- Claude: hard `tools:` allowlist. `engineer` and `reviewer` use `model: inherit`; `runner` uses `haiku`.
- Codex: `sandbox_mode: read-only` on every shipped profile. Profiles carry no model or effort because Agent Bundler does not render those fields; `engineer` is excluded by package policy.
- Pi: sidecar `tools` lists plus body directives; `advisor` and `runner` rely on the directive to keep `bash` read-only.
- Copilot, Cursor, Grok: portable artifacts without a cc-thingz runtime envelope.

## Routing rules

- Keep `engineer` the sole mutator. Override the model for one call instead of adding a cheaper engineer role.
- Role descriptions omit "Use proactively" because the orchestrator selects them to pair with a skill. `runner` opts in because it is a utility lane.
- Keep Pi agent frontmatter model-agnostic: no `model` or `thinking` keys. Users set model policy in `~/.pi/agent/settings.json` or `.pi/settings.json`. Retry and model-switch policy is in [docs/pi-extensions.md](docs/pi-extensions.md#models-and-retries).
- Cross-tool routing policy belongs in the chezmoi-managed top-level `CLAUDE.md`; repo role boundaries and package rules belong here.

## Repository rules

- Instruction files: follow the `writing-skills` skill. `make lint-instructions` is an advisory check.
- Deleting, renaming, or merging a skill also updates `tests/skill-evals/**`, package JSONs, tests, and README mentions.
- Python tooling runs through `uv`.

## Releases

- Prepare with `scripts/release/release-tag prepare vX.Y.Z`, write the `CHANGELOG.md` section, and commit it together with everything `prepare` changed (version manifests, `uv.lock`, regenerated `dist/`) in one commit. Then run `scripts/release/release-tag finalize vX.Y.Z` on that commit. Finalize runs `make ci` and creates a local annotated tag; it does not push.
- Pushing that tag is the only way to publish: `.github/workflows/release.yml` creates the GitHub release.
- Notes-only repair uses the same workflow's manual run from the default branch (other refs no-op), with the existing tag and a full `notes_source_sha`.
- Do not run `gh release create` or `gh release edit` here. Details: [CONTRIBUTING.md](CONTRIBUTING.md#releases).
