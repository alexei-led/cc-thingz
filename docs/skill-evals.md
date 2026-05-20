# Skill evals

Skill evals are paid LLM regression tests for `SKILL.md` behavior. Keep them out of deployable plugin skill directories.

## Layout

Store fixtures under `tests/skill-evals/<plugin>/<skill>/`:

```text
tests/skill-evals/dev-tools/using-modern-cli/
└── evals/
    ├── evals.json
    └── files/
        └── optional-fixture.txt
```

`make skill-evals-prepare` copies the matching deployable skill from `plugins/<plugin>/skills/<skill>/` into `/tmp/cc-thingz-skill-eval-root` and injects `evals/` there. This gives `agent-skills-eval` the layout it expects without shipping evals in plugin packages.

Use `SKILL_EVAL_SOURCE=skills-codex` to test the Codex/Gemini overlays while preserving the evaluator's expected `plugins/<plugin>/skills/<skill>/` output layout. Pi exports are validated locally by `make validate`; paid eval preparation currently supports source skills and Codex/Gemini overlays only.

`make validate` runs `validate-no-plugin-evals`, which fails if `plugins/*/skills/*/evals` exists.

## Basic eval file

```json
{
  "skill_name": "using-modern-cli",
  "evals": [
    {
      "id": "rewrite-legacy-shell-commands",
      "name": "rewrite legacy shell commands",
      "prompt": "Rewrite grep/find/cat/ls commands with modern CLI tools.",
      "expected_output": "The response uses rg, fd, bat, eza, dust, and procs.",
      "assertions": [
        "The output uses rg instead of grep for text search.",
        "The output uses fd instead of find for file discovery."
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
make skill-evals SKILL_EVAL_INCLUDE='dev-tools/skills/using-modern-cli'
```

Run against exported Codex/Gemini skill overlays:

```bash
make skill-evals SKILL_EVAL_SOURCE=skills-codex
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
make skill-evals-fast SKILL_EVAL_INCLUDE='dev-tools/skills/analyzing-usage'
```

Run source skills and Codex/Gemini overlays in parallel with separate workspaces:

```bash
make skill-evals-both SKILL_EVAL_STRICT=0
```

Speed knobs:

- `SKILL_EVAL_BASELINE=0` halves target/judge work by skipping `without_skill` mode.
- `SKILL_EVAL_HTML_REPORT=0` skips static report generation; JSONL and Markdown summary remain.
- `SKILL_EVAL_CONCURRENCY=8` roughly doubles parallel eval calls versus the default 4, subject to provider rate limits.
- `SKILL_EVAL_INCLUDE='plugin/skills/skill-name'` runs one skill instead of the full suite.
- `SKILL_EVAL_JUDGE=gpt-5.4-nano` can make judging cheaper/faster for iteration; use the default judge before trusting final numbers.

Use `SKILL_EVAL_LOG_FORMAT=pretty` only for small one-skill runs. The upstream `silent` mode still emits pretty logs because the SDK installs a default reporter when no reporter is passed. Naturally.

Use a cheaper judge:

```bash
make skill-evals SKILL_EVAL_JUDGE=gpt-5.4-nano
```

Defaults:

- target: `gpt-5.4-mini`
- judge: `gpt-5.4-mini`
- workspace: `/tmp/cc-thingz-skill-eval-workspace`
- prepared root: `/tmp/cc-thingz-skill-eval-root`
- skill source: `skills` (`skills-codex` for exported Codex/Gemini overlays; Pi uses local validation)
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
