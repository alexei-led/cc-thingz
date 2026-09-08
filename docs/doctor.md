# Installation doctor

The doctor ships as a checkout CLI (`make doctor`), not as a standalone
installed plugin capability. It requires this repository's canonical manifests.

The doctor compares resources on disk with this checkout's source package
manifests. It identifies stale package versions, old package names, duplicate
skill directories, missing skill helpers, missing Codex agent profiles, and
exact duplicate hook registrations within one manifest.

It does not execute commands, hooks, helpers, or package managers; contact the
network; change installation files; or read credentials. Hook commands are
compared in memory and never included in output. JSON errors do not echo file
contents. Use Python's `-B` option to avoid interpreter bytecode writes.

## Run

```bash
uv run python -B scripts/diagnostics/doctor.py
uv run python -B scripts/diagnostics/doctor.py --json
uv run python -B scripts/diagnostics/doctor.py \
  --plugin-root dist/codex --config-root dist/codex/.codex --json
```

The script itself uses only the Python standard library. On an installation
where uv would need to populate its cache, invoke an existing Python 3.12+
interpreter directly with `-B` for an entirely read-only invocation.

Without root options, it checks the Codex cc-thingz marketplace cache under
`~/.codex/plugins/cache/alexei-led-cc-thingz` and flat skills under
`~/.codex/skills` and `~/.agents/skills`. It does not assume that cached packages
are enabled. A duplicate means multiple copies on disk, not proven duplicate
execution. Multiple cached versions can legitimately produce findings.

With any explicit root option, only supplied roots are inspected. Use repeated
`--plugin-root` and `--skill-root` options for multiple locations. Each plugin
root can be a plugin directory, target distribution directory, or marketplace
cache. The scanner recognizes `.codex-plugin/plugin.json` and
`.claude-plugin/plugin.json` at the root or up to three directory levels below
it. Flat skill roots use the conventional `<skill>/SKILL.md` layout; identities
come from directory names. Expected skill files respect the source package asset target restrictions.
Custom skill-directory declarations and other vendor
installation layouts are outside this first version.

`--config-root` selects a Codex `.codex` directory and checks for advisor,
reviewer, and runner TOML files under `agents/`. It does not read the profiles
or prove that the runtime loads them. Without this option, that check is skipped.
Use `--repo` to compare against another cc-thingz checkout.

The CLI exits 1 when any check fails, 0 otherwise; argument errors exit 2.
Skipped and unsupported checks remain visible even on exit 0. Exit 0 does not
mean a complete runtime verification. Runtime activation, event support,
external helper dependencies, and effective permissions are explicitly
unsupported by this static check.

## Migrate old packages

Review enabled packages in the runtime's own manager before removing anything.
Install the replacements that cover the skills you use, verify discovery in a
fresh session, then disable the superseded packages. Cache directories alone
cannot tell you which copies are loaded. The doctor never deletes them.

- `dev-tools` → `discovery` and `git-flow`.
- `dev-workflow` → `dev-flow`.
- `spec-dev` → `spec-flow`.
- `go-dev`, `py-dev`, `python-dev`, `rust-dev`, `ts-dev`, `typescript-dev`,
  `web-dev` → `programming`.
- `test-e2e`, `browser-automation` → `browser`.

These are review suggestions, not a one-to-one promise that every historical
skill survives. Compare the canonical skill list in the report with your usage.

## Check result contract

JSON output has `schema_version: 1`, `canonical_packages`, `plugins`, `skills`,
and `checks`. Package inventory includes names, versions, and source paths.
Each check has:

- `check`: stable check category.
- `status`: `passed`, `failed`, `skipped`, or `unsupported`.
- `reason`: the observation or reason the check could not run.
- `command`: argument array for an executed command, or null. Always null here.
- `cwd`: checkout used for the comparison.
- `scope`: inspected paths, or the missing paths for an incomplete resource set.
- `timestamp`: UTC observation time.

`passed` applies only to the stated check and scope. `skipped` means an optional
input was absent. `unsupported` means this tool cannot establish the property.
The result is an observation, not an attestation or content fingerprint. A
consumer must rerun checks after files change; timestamps do not establish that
a result still describes the current files. Other helpers can adopt these
fields without depending on the doctor's implementation. There is no command
planner or shared execution framework in this version.
