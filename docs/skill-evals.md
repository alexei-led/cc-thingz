# Skill evals

Skill evals are paid LLM regression tests for `SKILL.md` behavior. Keep them out of deployable plugin skill directories.

## Layout

Store fixtures under `tests/skill-evals/<plugin>/<skill>/`:

```text
tests/skill-evals/discovery/reviewing-instructions/
└── evals/
    ├── evals.json
    └── files/
        └── optional-fixture.txt
```

`<package>` must match the current package ID from `src/.agentbundler/packages/<package>.json`.

`make skill-evals-prepare` copies the matching built skill from `dist/claude/<plugin>/skills/<skill>/` into `/tmp/cc-thingz-skill-eval-root` and injects `evals/` there. This gives `agent-skills-eval` the layout it expects without shipping evals in plugin packages.

Skill eval preparation copies the Claude package layout rendered by Agent Bundler into the evaluator's expected package/skill tree. Pi exports are validated locally by `make validate`; paid eval preparation does not run vendor-specific overlays.

CI runs deterministic preparation separately from paid scores. Unknown fixture identities fail preparation; intentionally retired scenarios are listed in `tests/skill-evals/migrations.json`. Run `--inventory` for the current source of truth: active scenario and skill counts, archived scenarios with their reasons, and any uncovered skills — don't hard-code those numbers here, since they drift every time a skill or fixture is added, removed, or merged. `--out` must be new or carry the preparer's exact-path ownership marker; an old unmarked temporary tree is refused. Trees containing entries absent from the ownership record are also refused. Choose a fresh path rather than deleting unknown contents. Release tests check that eval fixtures are not shipped inside deployable skills.

## Basic eval file

```json
{
  "skill_name": "reviewing-instructions",
  "evals": [
    {
      "id": "clean-result-keeps-scores",
      "name": "clean result keeps scores",
      "prompt": "Review a clean AGENT.md and describe the required output contract.",
      "expected_output": "The response keeps Summary and per-file Scores with evidence, and uses No confirmed findings only for Findings.",
      "assertions": [
        "The output keeps the Summary section.",
        "The output keeps per-file Scores with evidence."
      ]
    }
  ]
}
```

Each object in `evals[]` is one test case. Add multiple objects for multiple scenarios. The runner executes each case with the skill loaded and, when `--baseline` is enabled, without the skill loaded.

## Useful fields

- `id`: stable machine-readable case id. Use kebab-case.
- `name`: readable case name for reports.
- `prompt`: the exact user task sent to the target model.
- `expected_output`: short summary of success. If `assertions` is omitted, this becomes the only judge assertion.
- `assertions`: rubric items graded by the judge. Keep them concrete and observable.
- `files`: fixture paths relative to the skill root, usually `evals/files/...`.
- `params`: target model parameters for this case. Merged over defaults.
- `tools`, `tool_choice`: OpenAI-compatible function tools available to the target model.
- `tool_assertions`: deterministic checks on structured tool calls. These do not need the judge model.

Assertion entries can be strings or objects with `text`, `value`, or `criterion`:

```json
{
  "assertions": [
    "The output cites handler.ts.",
    { "text": "The output recommends parameterized queries." }
  ]
}
```

## Defaults

Use top-level `defaults` for shared model params or tools:

```json
{
  "skill_name": "example-skill",
  "defaults": {
    "target": { "params": { "max_tokens": 1200 } },
    "judge": { "params": { "max_tokens": 1000 } }
  },
  "evals": []
}
```

Avoid setting temperature unless the chosen model supports it. The local Makefile currently passes no params by default.

## Fixtures

Fixtures are inlined into the user prompt when the provider does not support native attachments.

```json
{
  "id": "review-diff",
  "prompt": "Review the attached diff for security issues.",
  "files": ["evals/files/sql-injection.diff"],
  "assertions": [
    "The output identifies SQL injection.",
    "The output cites the vulnerable line from the diff."
  ]
}
```

Keep fixtures small. The evaluator skips or marks files that are missing, binary, or too large.

## Tool-call assertions

Use `tool_assertions` when the target model returns OpenAI tool calls and you want deterministic checks:

```json
{
  "id": "calls-search-tool",
  "prompt": "Search for TODO comments.",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search",
        "description": "Search files",
        "parameters": {
          "type": "object",
          "properties": { "query": { "type": "string" } },
          "required": ["query"]
        }
      }
    }
  ],
  "tool_assertions": [
    { "type": "tool-called", "name": "search" },
    {
      "type": "tool-arg-contains",
      "name": "search",
      "path": "query",
      "value": "TODO"
    }
  ]
}
```

Supported assertion types: `tool-called`, `tool-not-called`, `tool-arg-equals`, `tool-arg-contains`, `tool-arg-matches`, `tool-call-count`.

## Local commands

Run all local skill eval fixtures:

```bash
make skill-evals
```

Run one skill:

```bash
make skill-evals SKILL_EVAL_INCLUDE='discovery/skills/reviewing-instructions'
```

Validate Pi exports without paid model calls:

```bash
make build validate
```

The target writes event logs to JSONL and prints a fix-focused summary:

- `WITH-SKILL FAILURES TO FIX` — real failures in the skill path. Fix these.
- `WITHOUT-SKILL FAILURES` — baseline misses. These are useful lift signal, not failures to fix.
- `LOWEST WITH-SKILL PASS RATES` — skills to inspect first.
- `output:` paths — full model outputs for debugging.
- `report:` — HTML report with prompts, outputs, judge evidence, and timing.

Reprint the latest summary without rerunning paid evals:

```bash
make skill-evals-summary
```

The summary also writes Markdown to:

```text
/tmp/cc-thingz-skill-eval-workspace/summary.md
```

Run faster with more parallel eval cases:

```bash
make skill-evals SKILL_EVAL_CONCURRENCY=8 SKILL_EVAL_LOG_FORMAT=jsonl
```

Fast fix loop, no baseline and no HTML report:

```bash
make skill-evals-fast SKILL_EVAL_INCLUDE='discovery/skills/researching-web'
```

Speed knobs:

- `SKILL_EVAL_BASELINE=0` halves target/judge work by skipping `without_skill` mode.
- `SKILL_EVAL_HTML_REPORT=0` skips static report generation; JSONL and Markdown summary remain.
- `SKILL_EVAL_CONCURRENCY=8` roughly doubles parallel eval calls versus the default 4, subject to provider rate limits.
- `SKILL_EVAL_INCLUDE='plugin/skills/skill-name'` runs one skill instead of the full suite.

Use `SKILL_EVAL_LOG_FORMAT=pretty` only for small one-skill runs. The upstream `silent` mode still emits pretty logs because the SDK installs a default reporter when no reporter is passed. Naturally.

Defaults:

- target: `gpt-6-luna`
- judge: `gpt-6-luna`
- workspace: `/tmp/cc-thingz-skill-eval-workspace`
- prepared root: `/tmp/cc-thingz-skill-eval-root`
- skill source: Agent Bundler's Claude package output; Pi uses local validation
- baseline: enabled (`SKILL_EVAL_BASELINE=0` disables it)
- HTML report: enabled (`SKILL_EVAL_HTML_REPORT=0` disables it)
- concurrency: `4`
- event log: `/tmp/cc-thingz-skill-eval-workspace/events.jsonl`
- Markdown summary: `/tmp/cc-thingz-skill-eval-workspace/summary.md`

Reports are written to:

```text
/tmp/cc-thingz-skill-eval-workspace/iteration-N/report/index.html
```

## Good eval design

- Test one behavior cluster per case.
- Use 3-8 concrete assertions per case.
- Prefer positive assertions: "uses ast-grep for structural search" or "uses rg for text search" is easier to grade than "does not use grep".
- Avoid broad assertions like "is good" or "is idiomatic".
- Include edge cases where the baseline likely fails.
- Keep prompts realistic, not keyword traps.
- Keep IDs stable so reports can be compared across runs.
- Boundary/routing tests (which skill should fire?) find the most useful failures.
- If a skill has good instructions but the model omits them, the prompt probably needs to demand command-level detail.
- If the judge makes a bad call, rewrite the assertion to be more concrete instead of trusting vibes. Obviously.
- The target gets one turn and runs no tools. Put every fact it would otherwise ask for (command output, code, config) in the prompt, and ask for the exact commands and changes it would make. Otherwise the skill arm asks for the repo and scores zero.
- Assert on what the output proposes ("the output's command is ..."), one claim per assertion. The judge fails "runs X" when the output says nothing was run, and fails compound "X, because Y" assertions on the second clause.

## Reading a run

- `WITH-SKILL FAILURES TO FIX` is the action list — fix these.
- `WITHOUT-SKILL FAILURES` are lift signal, not bugs to chase.
- `LOWEST WITH-SKILL PASS RATES` flags skills to inspect first.

## Cost and CI policy

`make test` stays free and deterministic. `make skill-evals` is paid and explicit.

Do not run skill evals on untrusted PRs with secrets. CI runs them only on trusted branches or same-repo PRs when skill/eval paths change, plus manual `workflow_dispatch`.

CI skill evals are advisory for now: failures write warnings, upload artifacts, and populate the GitHub step summary, but do not fail the whole CI workflow. Local `make skill-evals` remains strict by default.

Use advisory mode locally when you want the same behavior:

```bash
make skill-evals SKILL_EVAL_STRICT=0
```

## Agentic evals (`claude plugin eval`)

The single-turn harness above (`make skill-evals`, `agent-skills-eval`) grades what a
model _says_ it would do, with no tools. `claude plugin eval` runs a real Claude Code
agent — tools, multi-turn, an optional no-plugin baseline arm, and a `tool_used: Skill`
grader that shows whether the skill actually fired. See `claude plugin eval --help` for
the full flag reference. It's a different, complementary signal, not a replacement —
`make skill-evals` stays the cheap cross-model check.

### Layout

Like the single-turn harness, fixtures never ship inside a built plugin. Store them
under `tests/plugin-evals/<package>/<skill>/evals/<case>/`:

```text
tests/plugin-evals/git-flow/using-git-worktrees/evals/smoke/
├── prompt.md          # frontmatter: max_turns, allowed_tools; body is the task
└── graders/
    └── criteria.md    # frontmatter: type (llm), weight; body is the rubric
```

`<package>` and `<skill>` must match a compiled `dist/claude/<package>/skills/<skill>/`
directory. Use `claude plugin eval init --bare <name>` (from any plugin folder) to see
the exact frontmatter shape before hand-writing a case.

### Running it

```bash
make plugin-evals-prepare PLUGIN_EVAL_PACKAGE=git-flow   # free: copies dist/claude/<package>,
                                                           # layers evals/ from tests/plugin-evals/
make plugin-evals PLUGIN_EVAL_PACKAGE=git-flow            # paid: claude plugin eval against the copy
```

`scripts/evals/prepare-plugin-evals.py --package <name> --out <dir>` copies the built
plugin into an owned scratch tree (same ownership-marker safety model as
`prepare-skill-evals.py`) and injects the matching fixtures — this is what keeps eval
prompts and graders out of `dist/` and out of released plugin packages. Run
`--inventory` to see which packages/skills currently have fixtures without writing
anything.

`make plugin-evals` always sets `--max-cost-usd` (`PLUGIN_EVAL_MAX_COST`, default
`1.00`) and `--ablation with-without`; pass `EXTRA_ARGS='--case ... --runs ...'` to
narrow a run. One package per targeted run, with a fresh `PLUGIN_EVAL_ROOT` when
comparing before/after — `claude plugin eval`'s own `--json`/`--report` flags cover
report output.

### Status

Pilot only, as of v6.17.0 planning. The harness plumbing (prepare script, make
targets) is built.

`git-flow/using-git-worktrees` (a scripted skill) has a 4-case suite —
`create-parallel-dirty-main`, `cleanup-after-merge-no-gh`,
`conflict-branch-checked-out-elsewhere` (fire), `simple-branch-switch-no-worktree`
(should-NOT-fire) — sourced from the existing `tests/skill-evals` cases and
rewritten for live tool use, each with a `context.scaffold_script` that stands up a
throwaway git repo. Paid-piloted across several `--runs 1 --ablation none` calibration rounds
(~$3.38 total so far); `runs: 3 --ablation with-without` (the real suite) is
running as of this writing.

Calibration found, in order:

1. Every `tool_used` grader using `max: 0` needs an explicit `min: 0` — the schema
   defaults `min` to 1, so an unset `min` alongside `max: 0` asserts an impossible
   `1..0` range and always fails regardless of behavior. Fixed in all three
   affected graders.
2. `Skill` is not implicitly grantable — a run needs `--allow-tools Bash,Skill`
   explicitly, or `Skill` calls get denied under `dontAsk` permission mode.
3. `execution.env` in `case.yaml` only accepts `EVAL_*`-prefixed keys — a case
   cannot set `PATH` (or anything else) to route around a broken tool in the
   sandbox. Tried this to route `git` calls around an `/usr/bin/git` that failed
   to write its cache in the sandbox on `create-parallel-dirty-main`; reverted
   rather than fight the boundary, and dropped that case's
   `ran-setup-script-for-feature-auth` grader (it was checking a literal script
   invocation the sandbox artifact could legitimately make an agent route around;
   the case's outcome-based `worktree-created-and-explained` llm grader covers
   the same ground without depending on exact invocation form).
4. **Real routing gap, found and fixed.** `cleanup-after-merge-no-gh` scored 0.14
   twice running: the skill never fired for "remove this worktree and its branch"
   — the model ran plain `git` directly. Root cause: `using-git-worktrees`'
   frontmatter `description` only advertised creating worktrees, never mentioned
   removing one, so the router had no reason to consider it for a cleanup ask even
   though the skill body already has a whole "Clean up one worktree" section.
   Fixed the description (now explicitly covers removing one worktree/branch
   after merge, while still routing bulk/stale sweeps to `cleanup-git`). Rebuilt
   `dist/` and re-piloted: all 4 cases scored 1.0.

With the routing fix and the dropped grader, `--ablation none` now scores 1.0
across all four cases — clean, but not discriminating on its own (a suite where
nothing fails says nothing round-to-round). The `--ablation with-without` pass
(`--runs 1`, $2.15) is what actually tests the delta, and it splits cleanly:

| case                                    | with | without |       Δ |
| --------------------------------------- | ---: | ------: | ------: |
| `cleanup-after-merge-no-gh`             |  1.0 |     0.2 | **0.8** |
| `conflict-branch-checked-out-elsewhere` |  1.0 |     1.0 |       0 |
| `create-parallel-dirty-main`            |  1.0 |     1.0 |       0 |
| `simple-branch-switch-no-worktree`      |  1.0 |     1.0 |       0 |

Real uplift lives entirely in the cleanup flow — without the skill the model still
attempts cleanup (12 turns) but doesn't reliably reach for `cleanup-worktree.sh`,
and its gh-confirmation-gap explanation is inconsistent (2/3 judge votes fail).
The create flow and the negative case show **zero** measured lift: a capable
model already sets up a worktree correctly, and already avoids creating one for a
plain branch switch, with no skill guidance at all. This is `runs: 1` (noise
unmeasured — the 0/0/0 deltas could firm up or wobble at `runs: 3`), but the
0.8 vs. flat-0 split is a clean early read: this skill's value concentrates in
one specific procedural rule (use the bundled cleanup script; confirm the merge;
be careful with `--force`), not in general worktree know-how. Relevant input for
the later slim/hillclimb pass once the harness covers more skills.

Running total spent across all calibration rounds so far: **~$5.53**.

`dev-flow/reviewing-code` (a knowledge skill, most-used per `usage-report.md`) has
no suite yet. The plan was to source it from real session transcripts, but that
scan was blocked outright by this environment's permission classifier (bulk reads
of personal transcript content, flagged as PII handling) — not narrowed, not
retried through another tool. Next attempt reframes the existing
`tests/skill-evals/dev-flow/reviewing-code` cases the same way `using-git-worktrees`
was done, instead of live transcripts.

## Offline hook routing probes

Measure skill-enforcer suggestions against curated English/Russian prompts without
calling any model:

```bash
uv run python scripts/evals/evaluate-skill-routing.py
uv run python scripts/evals/evaluate-skill-routing.py --disabled
```

Use `--hook /path/to/previous/hook.sh` to compare a saved hook revision against
the same fixtures. JSON includes hook and fixture hashes, per-case unexpected
and missing hints, precision among allowed hints, recall of required hints,
language breakdowns, and nonzero hook exits. Missing denominators are `null`,
not perfect scores. A successful command means the probes executed; mismatches
remain advisory data in the report.

The dataset is `tests/skill-evals/routing/prompts.json`. It includes Slack channel
and JavaScript async/await negatives, ordinary development positives, and Russian
requests with and without English technical tokens. This measures hint matching
on a small curated set. It does not measure actual skill activation, task quality,
model cost, or representative multilingual performance. Required misses when the
hook is disabled are expected and do not imply the model cannot select skills.

The 2026-09-08 repair probe preserved in
`tests/skill-evals/routing/results-2026-09-08.json` used 26 cases. Unexpected
hints fell from eight to zero while required-hint recall stayed at 15/19.
All four missing hints were Russian requests without English technical tokens.
Native nonzero exits fell from 26 to zero. The fixes were informed by this
dataset, so these numbers are regression evidence, not held-out performance.
Keep the hook advisory; use native skill descriptions for broader intent routing.
