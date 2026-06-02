# Claude Model Context

Applies to Claude agents/skills (any version). Universal rules and scoring dimensions are in
`references/scoring-rubric.md`. This file adds Claude-specific behavioral traits and the
Opus-specific (O-prefix) and Sonnet-specific (S-prefix) lint rules.

## Behavioral traits and model-specific rules

### Opus (model: opus)

Documented tendency: "excessive time exploring codebase, studying related patterns, or
investigating tangential concerns before executing the straightforward task" (SC p.103).
Prompting does not suppress over-eagerness on impossible tasks (SC p.92).

Lint rules — severity: warning:

- **O-EFFICIENCY** — body contains efficiency-bounding language ("focused", "stay focused",
  "don't over-explore", "efficient", "concise").
- **O-SCOPE-ONLY** — body contains "ONLY these" or "exclusively" or "Focus … ONLY".
- **O-EFFORT-MATCH** — if `effort: high`, body has at least 3 distinct focus area sections.
  High effort must be justified by genuinely complex multi-dimensional tasks. Severity: info.

### Sonnet (model: sonnet)

Documented tendency: lecture users on suboptimal requests (SC p.72); over-eagerness on
explicit non-exploratory actions (SC p.73). Anti-eagerness instructions are highly effective
on Sonnet — unlike Opus where prompting does not decrease the behavior (SC p.73-74).

Lint rules — severity: warning:

- **S-NO-LECTURE** — body does NOT contain lecture-inducing patterns ("explain why … wrong",
  "educate the user", "tell them why").
- **S-DECISIVE** — body contains decisive action language ("execute", "act", "decisive",
  "complete", "deliver", "propose"). Severity: info.
- **S-ANTI-EAGER** — body contains anti-eagerness language ("do not fabricate", "report …
  impossible", "do not take unapproved", "ask … before").

### Haiku (model: haiku)

Lighter reasoning budget. Instructions should be more explicit and step-by-step.
Apply only universal (U-prefix), format (F-prefix), and skill-structure (K-prefix) rules.
No O-prefix or S-prefix rules.

## Prompting best practices

- Be explicit and direct — Claude follows instructions literally; ambiguity causes interpretation errors.
- Explain the why behind critical constraints — Claude uses intent to handle edge cases better than rigid rules.
- Long instruction files cause rule amnesia. If Claude ignores a rule, the file is too long.
- Tool-grounded analysis reduces hallucination ("use tools as much as possible" improved both models on SWE-bench).
- Format signal hierarchy (MDEval benchmark): `#` headers and numbered lists highest; bold medium
  (≤15% of lines); italic and tables lowest — avoid.
