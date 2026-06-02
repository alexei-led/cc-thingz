# Context Engineering Review Rubric

Review rules for Claude Code configuration derived from Anthropic's
"Effective Context Engineering for AI Agents" (2026) and
"Best Practices for Claude Code" documentation.

Each rule addresses a specific dimension of context efficiency. Rules are
grouped by category and have severity levels matching lint conventions.

---

## Context Budget (CB-\*) — Manage the finite attention resource

### CB-STARTUP: Session startup token budget

**Severity**: warning  
**Check**: Sum tokens in CLAUDE.md files + auto-activated skill bodies + hook startup output  
**Threshold**: <2K ideal, <4K acceptable, >6K bloated  
**Source**: "Context must be treated as a finite resource with diminishing
marginal returns." (Context Engineering, p.2) — "As context window tokens
increase, model accuracy retrieving that information decreases." (Context
Engineering, p.3)  
**Rationale**: Every token loaded at session start competes for attention
throughout the entire conversation. Heavy startup payloads degrade
instruction-following from the first turn.

### CB-FORK: Skills that read files must use `context: fork`

**Severity**: error  
**Check**: Skills with Read/Glob/Grep in allowed-tools have `context: fork` in frontmatter  
**Exception**: Skills that read only 1-2 specific files by path  
**Source**: "Detailed search context remains isolated within subagents; lead
agents focus on synthesizing results." (Context Engineering, p.10)  
**Rationale**: Without fork, file contents read by a skill persist in the
main context window, displacing earlier instructions and accumulating noise.

### CB-PROGRESSIVE: Prefer just-in-time over upfront loading

**Severity**: info  
**Check**: Skills/agents use runtime discovery (Glob, Grep, Bash) rather than
hardcoded file reads in their body  
**Source**: "Just in time approaches maintain lightweight identifiers and
dynamically load data via tools at runtime." (Context Engineering, p.6) —
"CLAUDE.md files drop into context initially; primitives like glob and grep
enable runtime navigation." (Context Engineering, p.7)  
**Rationale**: Upfront loading assumes relevance. Runtime discovery lets the
agent find what's actually needed, keeping context lean.

### CB-COMPACT-SAFE: Long-horizon skills preserve compaction signals

**Severity**: info  
**Check**: Skills with >5 phases or multi-step workflows include clear phase
markers (numbered steps, H2/H3 headings) that compaction can use as boundaries  
**Source**: "Compaction's art lies in selection decisions — overly aggressive
approaches lose subtle critical context becoming important later."
(Context Engineering, p.9)  
**Rationale**: Well-structured skills survive compaction with minimal
information loss because the summarizer can identify phase boundaries.

---

## Signal Density (SD-\*) — Maximize information per token

### SD-CLAUDE-MD: CLAUDE.md contains only non-derivable instructions

**Severity**: error  
**Check**: Each line passes the test: "Would removing this cause Claude to make mistakes?"  
**Anti-signals**: Standard language conventions, self-evident practices
("write clean code"), file-by-file descriptions, long tutorials  
**Source**: "If Claude keeps doing something you don't want despite having a
rule against it, the file is probably too long and the rule is getting lost."
(Best Practices) — "Bloated CLAUDE.md files cause Claude to ignore your
actual instructions!" (Best Practices)  
**Rationale**: Every unnecessary line dilutes the important lines. CLAUDE.md
is read every session — it's the highest-cost context component.

### SD-DESCRIPTION: Skill/agent descriptions are precise routing signals

**Severity**: error  
**Check**: Description contains specific trigger phrases that uniquely
identify when this component should activate  
**Anti-signals**: Generic descriptions ("helps with code"), missing trigger
phrases, overlapping with other component descriptions  
**Source**: "Input parameters must be descriptive, unambiguous, and leverage
model strengths." (Context Engineering, p.4) — "Tools should be...
extremely clear regarding intended use." (Context Engineering, p.4)  
**Rationale**: Descriptions are used by the model for routing decisions.
Ambiguous descriptions cause mis-activation or missed activation.

### SD-TOOL-MINIMAL: Agents have minimal tool lists

**Severity**: warning  
**Check**: Each tool in `allowed-tools` is actually used in the agent's body  
**Source**: "Bloated tool sets covering excessive functionality or creating
ambiguous decision points. If humans can't definitively choose appropriate
tools, agents cannot." (Context Engineering, p.5)  
**Rationale**: Every tool definition consumes tokens in the agent's context.
Unused tools waste budget and create choice ambiguity.

### SD-RETURN: Sub-agent responses are condensed

**Severity**: warning  
**Check**: Agent instructions specify expected output format with clear
scope (e.g., "report in under 200 words", structured tables, specific fields)  
**Source**: "Specialized sub-agents handle focused tasks with clean context
windows. Main agents coordinate high-level plans while subagents perform deep
work, returning condensed summaries (1,000-2,000 tokens)."
(Context Engineering, p.10)  
**Rationale**: Raw exploration results from sub-agents flood the parent
context. Condensed structured output preserves signal.

---

## Architecture (AR-\*) — Structural effectiveness

### AR-HOOK-DETERMINISTIC: Deterministic rules in hooks, guidance in CLAUDE.md

**Severity**: error  
**Check**: Rules requiring 100% enforcement (linting, file protection,
formatting) are implemented as hooks, not CLAUDE.md lines  
**Source**: "Unlike CLAUDE.md instructions which are advisory, hooks are
deterministic and guarantee the action happens." (Best Practices)  
**Rationale**: CLAUDE.md instructions can be ignored under context pressure.
Hooks execute unconditionally. Misplacement means critical rules fail silently.

### AR-SKILL-DEMAND: Domain knowledge in skills, universal rules in CLAUDE.md

**Severity**: warning  
**Check**: CLAUDE.md does not contain domain-specific workflows or specialized
knowledge that would be better served as an on-demand skill  
**Source**: "CLAUDE.md is loaded every session, so only include things that
apply broadly. For domain knowledge or workflows that are only relevant
sometimes, use skills instead. Claude loads them on demand without bloating
every conversation." (Best Practices)  
**Rationale**: Moving domain knowledge from CLAUDE.md to skills reduces
startup token budget by loading it only when relevant.

### AR-MODEL-MATCH: Model assignment matches task complexity

**Severity**: warning  
**Check**: Model tiers align with task demands:

- `opus`: Complex multi-dimensional reasoning, deep analysis, security review
- `sonnet`: Standard implementation, code review, structured workflows
- `haiku`: Lightweight tasks, documentation, simple scaffolding  
  **Source**: "Smarter models require less prescriptive engineering."
  (Context Engineering, p.12) — Opus/Sonnet system cards document distinct
  behavioral characteristics.  
  **Rationale**: Over-provisioning wastes cost and may introduce over-exploration
  (Opus). Under-provisioning risks quality failures on complex tasks.

### AR-VERIFY: Skills include self-verification steps

**Severity**: error  
**Check**: Skills that produce code, config, or artifacts include a
verification step (tests, lint, build, diff check)  
**Source**: "Claude performs dramatically better when it can verify its own work.
This is the single highest-leverage thing you can do." (Best Practices)  
**Rationale**: Without verification, Claude produces plausible-looking output
that may not actually work. Verification closes the feedback loop.

### AR-ISOLATION: Each agent has focused, single responsibility

**Severity**: warning  
**Check**: Agent body addresses one concern area; scope section explicitly
excludes adjacent concerns  
**Source**: "Clear separation of concerns — detailed search context remains
isolated within subagents." (Context Engineering, p.10)  
**Rationale**: Kitchen-sink agents accumulate context from multiple concerns,
degrading performance on each. Focused agents start with clean context.

---

## Anti-Patterns (AP-\*) — Known failure modes

### AP-TRIGGER-OVERLAP: Multiple components with ambiguous trigger overlap

**Severity**: error  
**Check**: No two skills/agents have description trigger phrases that would
match the same user prompt  
**Source**: "If humans can't definitively choose appropriate tools, agents
cannot." (Context Engineering, p.5)  
**Rationale**: When multiple skills match a prompt, the model may pick the
wrong one or waste tokens deciding. Each prompt pattern should map to
exactly one component.

### AP-SCOPE-UNBOUNDED: Agents without scope boundaries or exit criteria

**Severity**: error  
**Check**: Agents have explicit scope limits ("ONLY", "Do not", "exclusively")
and conditions for stopping  
**Source**: "You ask Claude to 'investigate' something without scoping it.
Claude reads hundreds of files, filling the context." (Best Practices)  
**Rationale**: Unbounded agents consume the entire context window exploring
tangentially, leaving no room for useful work.

### AP-OVER-SPECIFIED: Configuration is too long, causing rule amnesia

**Severity**: warning  
**Check**: CLAUDE.md >150 lines, skills >200 lines, agents >100 lines  
**Threshold**: Soft limits — content density matters more than line count  
**Source**: "Bloated CLAUDE.md files cause Claude to ignore your actual
instructions!" (Best Practices) — "Context rot: as context window tokens
increase, model accuracy retrieving that information decreases."
(Context Engineering, p.3)  
**Rationale**: Long instructions create the paradox of more rules leading to
worse compliance. Shorter, denser instructions outperform.
