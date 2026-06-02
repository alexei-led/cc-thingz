---
description: Structured stepwise reasoning with explicit revisions and branches. Use
  when the user says "think step by step", "sequential thinking", "plan this out",
  "reason through this", "branch this idea", or when tackling a hard multi-step problem
  (architecture decisions, ambiguous bugs, multi-constraint tradeoffs, plans that
  may need revision). NOT for trivial lookups, single-tool fetches, or tasks the model
  can answer directly without planning.
name: sequential-thinking
---

# Sequential Thinking

Replaces the `sequential_thinking` MCP server. Same intent — externalize a numbered chain of thoughts with revision and branch semantics — implemented as visible Markdown so any reasoning-capable model (Claude 4.x extended thinking, Gemini 3.x thinking, GPT-5.x reasoning) can follow it without an extra tool round-trip.

## When to use

- The problem has 3+ interacting constraints or sub-decisions.
- An earlier conclusion may need revising as new evidence arrives.
- More than one viable approach is on the table and they should be compared, not silently chosen.
- The user explicitly asked for stepwise/structured reasoning.

If none of these hold, answer directly — protocol overhead on a simple question wastes tokens and looks performative.

## Why a visible protocol (not just internal CoT)

Modern reasoning models already think internally. They need a shared on-the-page format so:

- the user can audit which step a wrong conclusion came from,
- revisions can point at the specific thought they replace,
- branches can be compared side by side instead of overwriting each other,
- a downstream agent or reviewer can parse the structure.

Do not try to suppress, expose, or paraphrase the model's hidden reasoning trace. Use this protocol in addition to it — write the durable, reviewable summary as Thought blocks; let the internal trace stay internal.

## Protocol

Open with a one-line plan, then emit numbered Thought blocks. Use these exact markers so output is parseable:

```
**Plan:** N thoughts (estimate). Subject: <one-line problem statement>.

### Thought 1
<the step — observation, deduction, sub-decision, or question>

### Thought 2
<...>

### Thought 3 (revises 1)
<corrected version, with one sentence on why 1 was wrong>

### Branch A from 2
<alternative path>

### Thought 4 (Branch A)
<continuation of A>

### Thought 5 (main)
<continuation of the main line>

### Final
<the conclusion or recommendation. Names the winning branch if any.>
```

### Block rules

- **Numbering is monotonic.** A revision gets a new number; it does not overwrite an old one. `(revises N)` declares which thought it supersedes.
- **Branches** are labelled `Branch <letter> from <N>`. Subsequent thoughts on that branch tag themselves `(Branch <letter>)`. The default trunk needs no tag.
- **Estimate, then adjust.** The opening `Plan:` is an estimate, not a contract. If you need more thoughts, write `### Thought N (extending plan to M)` and continue. Don't pretend you knew all along.
- **One thought, one move.** A thought makes one observation, one deduction, or asks one question. Walls of text under a single number defeat the point.
- **Final is mandatory.** Stop with `### Final`. Without it, callers can't tell whether you finished or got cut off.

### Grounding

When a thought references the codebase, cite `path:line` (or quote the relevant snippet). When a thought rests on an unverified assumption, prefix it `ASSUMPTION:` so revision can target it later. Do not invent file paths or function signatures to make a step sound concrete — an unsupported step is worse than no step.

### Verification gate (before `### Final`)

Run a brief checklist in the last numbered thought:

1. Does the conclusion follow from the evidence cited, or only from assumptions?
2. Is any thought contradicted by a later finding without a `(revises N)` marker fixing it?
3. Were the alternative branches actually compared, or just listed?
4. If the user asked for a recommendation, is one named — not hedged?

If any check fails, add one more Thought to address it before writing Final.

## Example (compressed)

> **Plan:** 4 thoughts. Subject: pick auth strategy for the new internal dashboard.
>
> ### Thought 1
>
> Existing services use OIDC via the company IdP (`infra/auth/oidc.go:42`). Reusing it avoids a new identity surface.
>
> ### Thought 2
>
> Dashboard needs short-lived tokens for embedded widgets. OIDC ID tokens are 1h; refresh is browser-side. ASSUMPTION: widgets stay in the same origin.
>
> ### Branch A from 2
>
> Service-to-service: signed JWT minted by the dashboard backend, 5min TTL. Avoids browser refresh edge cases for widgets.
>
> ### Thought 3 (Branch A)
>
> Backend already has the signing key from `internal/jwt/signer.go:18`. No new infra. Tradeoff: widgets can't run as the user, only as the dashboard.
>
> ### Thought 4 (revises 2)
>
> Re-checked: widgets DO call user-scoped APIs. Branch A breaks that.
>
> ### Thought 5
>
> Verification: conclusion (stay on OIDC) follows from Thought 4; Branch A explicitly rejected; recommendation named.
>
> ### Final
>
> Use OIDC end-to-end. Add a 5min cached token endpoint for widgets so each widget doesn't trigger its own refresh. Touch points: `internal/auth/`, `web/widgets/token.ts`.

Six blocks beats six paragraphs because every step has a number a reviewer can point at.

## When to stop early

If a thought reveals the question was wrong (wrong scope, missing requirement, blocked by an unknown), write one more Thought summarising the blocker, then `### Final` stating "blocked: <reason>, need <thing>". Don't keep generating thoughts to look thorough — half-finished structured reasoning is fine; pretending to finish is not.

## Anti-patterns

- Numbering stream-of-consciousness sentences as "thoughts" to hit a count.
- Writing `### Final` and then continuing with more thoughts. Final is terminal.
- Using `(revises N)` to extend a thought instead of correct it. New direction = new thought, not a revision.
- Branches that never resolve. Every branch must either be picked, rejected (with one-line reason), or explicitly deferred in Final.
