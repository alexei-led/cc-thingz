---
name: brainstorming-ideas
description: Brainstorm ideas and stress-test draft plans before coding. Use when user wants to brainstorm, explore approaches, design a feature/API/flow, grill a plan, challenge assumptions, or resolve terminology that blocks the design. NOT for breaking approved requirements into implementation tasks; use /spec:plan. NOT for general documentation updates; use documenting-code or learning-patterns.
user-invocable: true
context: fork
allowed-tools:
  - AskUserQuestion
  - Task
  - TaskCreate
  - TaskUpdate
  - TaskList
  - Read
  - Grep
  - Glob
  - Write
  - mcp__perplexity-ask__perplexity_ask
  - mcp__plugin_claude-mem_mcp-search__timeline
  - mcp__plugin_claude-mem_mcp-search__search
  - WebFetch
  - Bash(git *)
argument-hint: "[idea|plan|grill] <topic-or-plan>"
---

# Brainstorming Ideas

Turn a vague idea or draft plan into a clear design before coding. In grill mode, stress-test a plan until every important branch of the decision tree is resolved.

**Use TaskCreate / TaskUpdate** to track these 7 phases:

1. Understand the idea (dialogue first, no agents)
2. Explore requirements (Starbursting questions)
3. Checkpoint - offer exploration/research options
4. Research similar solutions (if requested)
5. Present approaches with recommendation
6. Validate design incrementally
7. Capture outcome and next steps

---

## Core Principles

- **Dialogue first** - Ask the user before spawning any agents
- **One question at a time** - Never batch multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended
- **"Other" always available** - Free text input for custom responses
- **YAGNI ruthlessly** - Challenge every feature's necessity
- **Incremental validation** - Present design in 200-300 word sections
- **Agents on request** - Only explore/research when user chooses it
- **Code over questions** - If the codebase can answer a question, inspect it instead of asking
- **Domain vocabulary matters** - Use `CONTEXT.md` / `CONTEXT-MAP.md` terms when present; resolve conflicts explicitly
- **ADRs are rare** - Offer one only for hard-to-reverse, surprising, real trade-off decisions

---

## Phase 0: Load Domain Context

Before asking design questions, check for project knowledge when relevant. Use Glob/Read to find the nearest relevant `CONTEXT.md`, `CONTEXT-MAP.md`, and `docs/adr/` files. If present, read them and use that vocabulary in questions and designs.

If no domain docs exist, create them lazily only when a term or decision is actually resolved. Do not generate empty documentation.

## Phase 1: Understand the Idea

Start with dialogue, not agents. Ask the user directly.

### 1a. Initial Question

Use AskUserQuestion:

| Header    | Question                           | Options                                                                                                                                                                                       |
| --------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Idea type | What would you like to brainstorm? | 1. **New feature** - Add new functionality 2. **Modification** - Change existing behavior 3. **Integration** - Connect with an external system 4. **Plan grill** - Stress-test an existing plan 5. **Exploration** - Not sure yet, let's discover |

### 1b. Follow-up (based on response)

Ask clarifying questions using AskUserQuestion. Keep it conversational:

- "Can you describe this in a sentence or two?" (free text via "Other")
- "What triggered this idea?" with context-appropriate options
- "Is there an existing feature this builds on?"

---

## Phase 2: Explore Requirements (Starbursting)

Ask questions **one at a time** using AskUserQuestion. Adapt based on idea type.

### Question Framework (5WH)

| Question Type | When to Ask                    | Example AskUserQuestion                                                              |
| ------------- | ------------------------------ | ------------------------------------------------------------------------------------ |
| **WHO**       | Always first                   | "Who will use this?" → Options: Existing users, New segment, Internal, API consumers |
| **WHY**       | After WHO                      | "What problem does this solve?" → Options based on detected pain points              |
| **WHAT**      | After WHY is clear             | "What's the core capability?" → Open or options based on research                    |
| **WHERE**     | For integrations/modifications | "Where should this live?" → Options based on codebase exploration                    |
| **HOW**       | After approach research        | "How should we implement?" → Present 2-3 technical approaches                        |

### Adaptive Questioning

- Skip questions when answers are obvious from context
- If user seems certain, move faster to approaches
- If user seems uncertain, explore deeper with sub-questions
- Use "Other" option to allow custom responses

### 2b. Plan Grill Mode

If the user passed `plan`, `grill`, or asked to stress-test/challenge a plan, interrogate the plan one decision at a time. Keep it focused on design quality and assumptions, not task breakdown; use `/spec:plan` for implementation tasks.

For each question:

- Provide your recommended answer.
- Explain why the branch matters.
- If the answer is discoverable from code, inspect code instead of asking.
- If a term conflicts with `CONTEXT.md`, call it out: "Your glossary defines X as A, but this plan uses X as B — which is it?"
- Use concrete scenarios and edge cases to force precision.

When a domain term is resolved, confirm before writing and update `CONTEXT.md` inline if the user approves the wording. Keep definitions one sentence. List aliases to avoid.

Offer an ADR only when all three are true:

1. Hard to reverse.
2. Surprising without context.
3. Result of a real trade-off.

### 2c. Surface Assumptions

Before moving on, explicitly list the assumptions embedded in the idea so far:

```
Based on our discussion, here are the assumptions I'm seeing:

1. [Assumption about users] — e.g., "Users want X in real-time"
2. [Assumption about tech] — e.g., "Our current DB can handle this load"
3. [Assumption about scope] — e.g., "This doesn't need to work offline"
```

Use AskUserQuestion:

| Header      | Question                                 | Options                                                                                                                             |
| ----------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Assumptions | Any of these assumptions wrong or risky? | 1. **All correct** - Proceed as-is 2. **Some wrong** - I'll clarify 3. **Not sure** - Let's validate the risky ones during research |

If "Some wrong": ask which ones and adjust requirements.
If "Not sure": flag risky assumptions for verification in Phase 4.

---

## Phase 3: Checkpoint - Gather More Context?

After understanding requirements, **ask before spawning any agents**:

| Header    | Question               | Options                                                                                                                                                                                                                                                                                      |
| --------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Next step | How should we proceed? | 1. **Explore codebase** - Check existing patterns and tech stack 2. **Research solutions** - Look up how others solve this 3. **Check project history** - Query past decisions on this topic (claude-mem) 4. **Both** - Explore then research 5. **Skip to approaches** - I know what I want |

### If user chooses "Explore codebase":

```
Task(
  subagent_type="Explore",
  prompt="Quick scan: project structure, tech stack, patterns relevant to [user's idea]",
  run_in_background=false
)
```

Then summarize findings and ask: "Based on this, should we also research external solutions?"

### If user chooses "Check project history":

If claude-mem tools are available:

```
search({ query: "[topic keywords]", limit: 10 })
timeline({ query: "[topic keywords]", depth_before: 5, depth_after: 5 })
```

Summarize past decisions, known issues, and relevant context. Then ask if they want to also explore or research.

### If user chooses "Research solutions":

Proceed to Phase 4.

### If user chooses "Skip to approaches":

Jump directly to Phase 5 (Present Approaches).

---

## Phase 4: Research Similar Solutions (If Requested)

Only run when user explicitly chose research in Phase 3.

### 4a. Perplexity Query

```
mcp__perplexity-ask__perplexity_ask({
  messages: [{
    role: "user",
    content: "How do leading [industry] products implement [feature type]? Include architectural patterns, UX approaches, and trade-offs. Focus on [tech stack] implementations."
  }]
})
```

### 4b. Follow Citations

After Perplexity response, WebFetch top 2-3 relevant sources:

```
WebFetch(url="<citation-url>", prompt="Extract implementation details, code patterns, and lessons learned for [feature]")
```

### 4c. Synthesize Findings

Present research summary before asking approach preference:

```markdown
## Research Findings

**Common patterns:**

- [Pattern 1]: Used by X, Y. Trade-off: ...
- [Pattern 2]: Used by Z. Trade-off: ...

**Recommended for our context:** [Pattern] because [reasons]
```

---

## Phase 5: Present Approaches

Use AskUserQuestion with 2-4 options:

| Header   | Question                  | Options                                                                                                                              |
| -------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Approach | Which approach fits best? | 1. **[Recommended]** - Description + key trade-off 2. **[Alternative]** - Description + key trade-off 3. **Minimal** - YAGNI version |

### Approach Template

For each option, briefly cover:

- **What**: Core implementation
- **Trade-offs**: Complexity vs flexibility, Now vs later
- **Fits when**: Scenario where this shines

---

## Phase 6: Validate Design Incrementally

Present design in sections (~200-300 words each). After each section, use AskUserQuestion:

| Header   | Question                        | Options                                                                                                                    |
| -------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Validate | Does this [section] look right? | 1. **Yes, continue** - Move to next section 2. **Needs changes** - I'll explain 3. **Go back** - Revisit earlier decisions |

### Design Sections

1. **Architecture Overview** - Components, responsibilities, relationships
2. **Data Flow** - How information moves through the system
3. **API/Interface** - External contracts and user interactions
4. **Error Handling** - Failure modes and recovery strategies
5. **Testing Strategy** - How to verify it works

### YAGNI Checkpoints

At each section, actively challenge:

- "Do we need this now, or is it speculative?"
- "What's the simplest version that solves the problem?"
- "Can we defer this complexity?"

---

## Phase 7: Capture Outcome and Next Steps

### 7a. Update Domain Docs Only When Needed

If the brainstorm resolved domain language, update `CONTEXT.md` or the relevant context file:

```markdown
## Language

**Term**:
One-sentence definition.
_Avoid_: fuzzy synonym, overloaded alias
```

If a qualifying architectural/product decision crystallized, create a short ADR under `docs/adr/NNNN-slug.md`:

```markdown
# Decision title

One to three sentences: context, decision, why.
```

Skip ADRs for easy-to-reverse, obvious, or no-real-alternative decisions.

### 7b. Write Design Notes If Useful

If the outcome is more than a short answer, offer to write a concise design note:

```text
docs/plans/YYYY-MM-DD-<topic>-design.md
```

Include only: Problem, Chosen approach, Trade-offs, Open questions, Testing strategy.

### 7c. Implementation Handoff

Use AskUserQuestion:

| Header     | Question                              | Options                                                                                                                                                           |
| ---------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Next steps | Ready to proceed with implementation? | 1. **Create worktree** - Isolated workspace via using-git-worktrees 2. **Create plan** - Detailed implementation steps 3. **Done for now** - Just save the design |

---

## Methodology Reference

This skill incorporates proven brainstorming techniques:

| Technique                 | How It's Used                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| **Starbursting (5WH)**    | Structured questions in Phase 2                                                             |
| **Design Thinking**       | Empathize (context) → Define (WHY) → Ideate → Prototype (design sections)                   |
| **SCAMPER**               | For modifications: Substitute, Combine, Adapt, Modify, Put to other use, Eliminate, Reverse |
| **Reverse Brainstorming** | "How could this fail?" during validation                                                    |
| **Mind Mapping**          | Architecture section visualizes relationships                                               |

---

## Examples

```
/brainstorming-ideas user notifications # Explore a feature idea
/brainstorming-ideas plan auth flow     # Shape a draft plan
/brainstorming-ideas grill migration    # Stress-test an existing plan
```

**Execute this collaborative brainstorming workflow now.**
