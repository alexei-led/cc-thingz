---
{"description":"Audit and improve AI coding-agent configuration. Use when reviewing or changing Claude Code, Pi, Codex, Copilot, Cursor, Grok, skill, agent, hook, MCP, permission, package, or generated-export setup. Default is review-only; fixes require explicit user approval or --fix. NOT for score-only instruction review or prompt lint; use reviewing-instructions. NOT for application config, git hygiene, code bugs, ordinary docs, or generated files without their source.","name":"evolving-config"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Read required skill/instruction files through direct read when exposed or through Code Mode. If an optional pruning extension is installed, verify its output protection semantics; do not assume nested-path protection. Code Mode composes calls; subagents or controllers own durable workflows. Async subagents notify natively: yield rather than poll. -->


# Evolving Agent Configuration

Audit AI coding-agent configuration and report prioritized, evidence-backed
findings with the smallest fix for each. Local files come first; official docs
and changelogs settle syntax, feature availability, and deprecation. Do not
recommend a change on the strength of an uncited blog.

For installed cc-thingz resource or version diagnostics, use installation-doctor
first and continue here for broader review or authorized changes.

## Limits

- Review-only by default. Change files only when the user asks for changes or
  passes `--fix`.
- Even in fix mode, ask before changing permissions, sandbox policy, hooks, MCP
  servers, model routing, package installs, deletes, moves, broad rewrites, or
  private or managed config.
- Edit sources, never generated exports; name the source path and the
  regeneration command instead.
- Never quote secret values; name only the path and key.

## Done

- Review: every finding cites a `path:line`, setting key, tool output, or doc
  URL, and findings are sorted by severity. With an unclear target, list the
  detected config surfaces and ask which to audit.
- Fix: only approved changes are applied. Done when the relevant
  build/test/lint checks pass on what you changed, or you name each check that
  did not run and why. Without write access, return proposed changes (file,
  change, reason) instead of applying them.

## References

- `references/RUBRIC.md` — severity and shared checks. Read for every audit.
- `references/platforms/claude-code.md`, `codex.md`, `pi.md` — read only the
  ones for platforms in scope.
- `references/platforms/other-targets.md` — read when the audit covers Copilot,
  Cursor, or Grok packages.
- `references/apply-fixes.md` — read only in fix mode.

## Scope

Instruction files (`AGENTS.md`, `CLAUDE.md`, prompts, skill and agent bodies),
the platform config each reference lists, plugin and package manifests, and
source-to-generated export rules. Include chezmoi or dotfile copies only when
deployment is part of the request.

## Output

Use finding tags such as `routing/thin-router`, `context/weak-pointer`, or
`invocation/over-model-invoked` when they sharpen the issue.

```markdown
## Config Audit

Scope: <platforms/files>
Mode: review-only | fix-approved
Sources: <local files and docs checked>
Confidence: high | medium | low

### Summary

- Files reviewed: N
- Generated files skipped: N
- Main risk: <one sentence>

### Critical

- `path:line` — <category[/subtype]>: <issue>. Evidence: <fact>. Fix: <action>.

### Important

- `path:line` — <category[/subtype]>: <issue>. Evidence: <fact>. Fix: <action>.

### Suggested

- `path:line` — <category[/subtype]>: <issue>. Evidence: <fact>. Fix: <action>.

### Working Well

- <config that should stay as-is>

### Verification

- <command run or recommended>
```

Omit empty severity sections. If no findings are confirmed, say `No confirmed
findings.` When official docs are unavailable, rely on local evidence, lower
confidence, and name the gap.

## Platform additions

Use the host's file search, read, and web fetch tools for inventory and docs.
