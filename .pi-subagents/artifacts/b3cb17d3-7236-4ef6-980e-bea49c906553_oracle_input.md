# Task for oracle

Advisory review only. Context: We are auditing cc-thingz Pi package agents for nicobailon/pi-subagents. User wants Pi to decide subagent model through current/default provider aliases. Current session model is router/auto-personal. Local settings defaultProvider=router defaultModel=auto-personal defaultThinkingLevel=xhigh; enabled models include router/auto-personal, router/auto-work, router/auto-claude-work, router/claude-work, router/claude-personal, openai-codex-personal/work models, anthropic-personal/work models. cc-thingz package agents currently pin Pi frontmatter model: engineer/reviewer openai-codex/gpt-5.4, runner openai-codex/gpt-5.4-mini, advisor openai-codex/gpt-5.5, with thinking high/medium/low/xhigh. pi-subagents docs/code show: explicit frontmatter model wins over subagents.defaultModel; no requested model resolves to parent in-memory provider/id; fallbackModels retries only provider/model failures; custom/package agentOverrides fill only frontmatter keys that are unset. Question: Should cc-thingz Pi agent frontmatter omit model entirely, use fallbackModels, keep/remove thinking, and which other frontmatter keys are appropriate? Return verdict, top risks, and concrete recommendations. Do not modify files.

## Acceptance Contract

Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:

- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```
