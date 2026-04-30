# Instruction Lint Rules

Model-aware lint rules for agent and skill instructions, derived from the Claude Opus 4.6
and Claude Sonnet 4.6 system cards. Each rule addresses a documented behavioral pattern
that instruction design can mitigate.

## Universal Rules (all models)

### U-SCOPE: Explicit scope boundaries

**Severity**: error
**Check**: Body contains scope-limiting language ("ONLY", "exclusively", "Do not", "no ... feedback")
**Why**: Both models improve instruction following when scope is explicit. Opus 4.6
over-explores without clear boundaries — "excessive time exploring the surrounding
codebase, studying related patterns, or investigating tangential concerns before
executing the straightforward task" (Opus SC p.103).

### U-OUTPUT: Defined output format

**Severity**: error
**Check**: Body contains output format section ("Output Format", "Output:", "Findings",
"Proposal Format", structured template markers like `###`)
**Why**: Hallucination and work-completion misrepresentation are reduced when output
format is constrained. Opus 4.6 misrepresents work completion at ~1.5% rate (Opus SC p.98).
Both models benefit from structured output expectations.

### U-TOOL-FIRST: Tool execution before manual analysis

**Severity**: warning
**Applies to**: Agents/skills with `Bash` in tools list
**Check**: Body contains bash code blocks before main analysis instructions
**Why**: SWE-bench prompt "use tools as much as possible" improved both Opus (80.8% to
81.4%) and Sonnet (79.6% to 80.2%) (Opus SC p.19, Sonnet SC p.15). Both system cards
emphasize tool-grounded analysis reduces hallucination.

### U-FAILURE: Failure/impossibility reporting

**Severity**: error
**Check**: Body contains failure-handling language ("impossible", "cannot", "report",
"If ... not available", "skip", "clean")
**Why**: Both models show over-eagerness — fabricating workarounds instead of reporting
failure. Opus 4.6 "frequently engaged in over-eager hacking to solve impossible tasks"
(Opus SC p.104). Sonnet 4.6 "would occasionally write and send the email itself based on
hallucinated information" (Sonnet SC p.73).

### U-GROUND: Ground claims in tool output

**Severity**: warning
**Check**: Body contains grounding language ("actual", "tool output", "include ... output",
"verify", "ground")
**Why**: Training data review found: "Claims to have used tools that failed or were never
called", "Hallucinations or misrepresentations about the output of tools" (Opus SC p.105).
Both models reduce hallucination when explicitly told to cite tool results.

### U-NO-DESTROY: Destructive action warnings

**Severity**: warning
**Applies to**: Agents/skills with write tools or broad/risky `Bash` permissions
**Check**: Body contains caution language ("force", "destructive", "careful", "caution",
"dangerous", "irreversible")
**Why**: "Safety and destructive action avoidance" is a key behavioral dimension.
Opus 4.6 "more consistently verifies preconditions before executing commands, warns users
when their instructions would cause data loss" (Opus SC p.103). Sonnet 4.6 "more careful
about flagging concerns and seeking confirmation" (Sonnet SC p.72).

## Opus-Specific Rules

### O-EFFICIENCY: Efficiency constraints

**Severity**: warning
**Applies to**: Agents with `model: opus`
**Check**: Body contains efficiency-bounding language ("focused", "stay focused",
"don't over-explore", "efficient", "scope", "concise")
**Why**: Opus 4.6 "works somewhat less efficiently than Opus 4.5 and is more likely to
spend slightly more time exploring and gathering context even when this is not strictly
necessary" (Opus SC p.103). Explicit efficiency constraints help counteract this.

### O-SCOPE-ONLY: Exclusive focus areas

**Severity**: warning
**Applies to**: Agents with `model: opus`
**Check**: Body contains "ONLY these" or "exclusively" or "Focus ... ONLY"
**Why**: Without explicit "ONLY" markers, Opus agents tend to expand scope — "studying
related patterns, or investigating tangential concerns before executing the straightforward
task" (Opus SC p.103). The existing go-qa agent demonstrates the pattern well:
"Focus Areas (ONLY these)".

### O-EFFORT-MATCH: High effort justification

**Severity**: info
**Applies to**: Agents with `model: opus` AND `effort: high`
**Check**: Body has at least 3 distinct focus area sections (H3 headings or numbered lists)
**Why**: `effort: high` increases cost significantly. Should only be used on agents with
genuinely complex multi-dimensional analysis tasks. Currently 6 agents use it — all
QA/impl specialists with 3+ focus areas.

## Sonnet-Specific Rules

### S-NO-LECTURE: Avoid lecture-inducing instructions

**Severity**: warning
**Applies to**: Agents with `model: sonnet`
**Check**: Body does NOT contain patterns that encourage lecturing ("explain why ... wrong",
"educate the user", "tell them why")
**Why**: "Sonnet 4.6 had an occasional tendency to lecture users in response to dangerous
or suboptimal requests, whereas other models flagged concerns but executed regardless"
(Sonnet SC p.72). Instructions should not amplify this tendency.

### S-DECISIVE: Decisive action language

**Severity**: info
**Applies to**: Agents with `model: sonnet`
**Check**: Body contains decisive action language ("execute", "act", "decisive", "complete",
"deliver", "propose")
**Why**: Sonnet 4.6 beats Opus and all models on efficiency but "sometimes performed
extensive investigation when the user asked it to perform an explicit non-exploratory action"
(Sonnet SC p.73). Decisive language reinforces the efficiency advantage.

### S-ANTI-EAGER: Anti-over-eagerness (steerable)

**Severity**: warning
**Applies to**: Agents with `model: sonnet`
**Check**: Body contains anti-eagerness language ("do not fabricate", "report ... impossible",
"do not take unapproved", "ask ... before")
**Why**: Sonnet 4.6 is "much more corrigible to system prompts discouraging these overly
agentic actions" (Sonnet SC p.73-74) — unlike Opus where "prompting does not decrease
this behavior" (Opus SC p.92). This makes anti-eagerness instructions particularly
effective for Sonnet agents.

## Skill Structure Rules

### K-NAME: Clear skill names

**Severity**: warning
**Applies to**: Skills
**Check**: Frontmatter `name` is kebab-case and not cryptic
**Why**: Skill names are surfaced to users and generated AGENTS.md catalogs. Opaque names
increase routing mistakes and make slash-command suggestions harder to understand.

### K-DESC: Trigger-rich descriptions

**Severity**: warning
**Applies to**: Skills
**Check**: Frontmatter `description` includes trigger language such as "Use when", "Use for",
"Auto-activates", or concrete activation contexts
**Why**: The description is the model's routing surface. A capability description without
triggers forces the model to infer when to load it, which increases routing mistakes.

### K-PROGRESSIVE: Progressive disclosure

**Severity**: warning
**Applies to**: Skills
**Check**: Skill body over 220 lines with no sibling support files
**Why**: Large monolithic skills dilute activation context. Keep `SKILL.md` focused on the
workflow and move rare reference detail into sibling files.

### I-ONE-QUESTION: Sequential interaction

**Severity**: warning
**Applies to**: Files using `AskUserQuestion`
**Check**: Body instructs one-question-at-a-time or sequential questioning
**Why**: Batched clarification questions create low-quality answers and hidden ambiguity.
Sequential prompts are slower in wall time, faster in reality.
