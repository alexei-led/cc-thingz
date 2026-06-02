# Scoring Rubric and Lint Rules

Scoring dimensions (0–10 each) used by the semantic review, plus the heuristic lint rules used
by the structural pre-pass (`lint-instructions.py`). Scores are authoritative; lint rules are
heuristic baselines that feed into dimension scores.

## Weights for overall score

Signal Density 15%, Scope Specificity 15%, Output Structure 15%, Failure Handling 15%,
Format Efficiency 10%, Grounding Discipline 10%, Routing Precision 10%, Progressive Disclosure 10%.

---

## 1. Signal Density

Every line earns its place with a non-derivable behavioral constraint. Lines removable without
behavior change score against this dimension.

- **0–2**: Majority is generic advice, rationale bloat, or tutorial-style prose
- **3–4**: Some constraints diluted by repeated rationale or verbose narrative
- **5–6**: Mostly actionable but 20–30% of lines are skippable
- **7–8**: Tight; ≤15% skippable content
- **9–10**: Every line is a behavioral constraint, workflow step, or concrete example. No filler.

No single lint rule. Check manually: "Would removing this line change the model's behavior?"

## 2. Scope Specificity

Explicit boundaries — what to do AND what not to do.

Lint rule: **U-SCOPE** — body contains scope-limiting language ("ONLY", "exclusively", "Do not",
"no … feedback"). Severity: error.

- **0–2**: No scope limits; instructions could justify almost any action
- **3–4**: Implicit scope; no explicit "do not" or exclusions
- **5–6**: Positive scope defined but no exclusions stated
- **7–8**: Explicit exclusions or "only these" markers for the main scope
- **9–10**: Clear in/out scope; exit conditions; neighbor-skill overlap explicitly resolved

## 3. Output Structure

The instruction defines a concrete output format.

Lint rule: **U-OUTPUT** — body contains output format section ("Output Format", "Output:",
"Findings", structured template markers like `###`). Severity: error.

- **0–2**: No output format; model must guess
- **3–4**: Output type mentioned but no structure
- **5–6**: Output described in prose; no template or example
- **7–8**: Template, required sections, or explicit field list provided
- **9–10**: Exact template with headers, fields, length bounds

## 4. Format Efficiency

Instruction uses only high-signal markdown elements.

Lint rules (all severity info/warning):

- **F-NO-TABLE** — no `| --- |` table syntax (use `- **Label**: desc` bullets instead)
- **F-NO-DIAGRAM** — no ` ```mermaid` blocks or ASCII box-drawing characters
- **F-NO-HR** — no standalone `---` horizontal rules outside frontmatter
- **F-NO-ITALIC** — no `_word_` or `*word*` italic in prose
- **F-BOLD-SPARSE** — bold on ≤15% of non-blank, non-code lines

Anchors:

- **0–2**: Multiple tables, diagrams, heavy italic, or bold >30% of prose lines
- **3–4**: 1–2 tables or diagrams; OR bold on 20–30% of lines
- **5–6**: No tables/diagrams but italic present; OR bold 15–20%; OR standalone HR
- **7–8**: Clean; only `#` headers, bullets, lists, code blocks; bold ≤15%; no standalone `---`
- **9–10**: Fully optimized: no tables/diagrams/italic/HR; bold reserved for labels and critical terms

## 5. Failure Handling

Behavior is specified when things go wrong.

Lint rule: **U-FAILURE** — body contains failure-handling language ("impossible", "cannot",
"report", "If … not available", "skip", "clean"). Severity: error.

Additional: **U-NO-DESTROY** — if agent has write tools, body contains destructive-action caution
("force", "destructive", "careful", "irreversible"). Severity: warning.

- **0–2**: No failure cases; model will fabricate workarounds or hallucinate completion
- **3–4**: Vague ("use your judgment if something fails")
- **5–6**: One or two failure cases explicitly covered
- **7–8**: Most predictable failures covered with specific vocabulary
- **9–10**: Comprehensive: missing input, unavailable tools, ambiguous data, impossible tasks — all explicit

## 6. Grounding Discipline

Outputs are evidence-anchored; claims cite tool output or file/line.

Lint rule: **U-GROUND** — body contains grounding language ("actual", "tool output",
"include … output", "verify", "ground"). Severity: warning.

Additional: **U-TOOL-FIRST** — for agents with Bash, body contains bash blocks before analysis
instructions. Severity: warning.

- **0–2**: No grounding requirement; model can state conclusions from inference
- **3–4**: Soft language ("try to cite sources")
- **5–6**: Grounding required but not uniformly enforced
- **7–8**: Explicit policy: findings must cite file/section; tool output must be referenced
- **9–10**: Strict: "No evidence, no finding"; verification step before reporting

## 7. Routing Precision

The description and name enable correct activation without false positives.

Lint rules:

- **K-NAME** — frontmatter `name` is kebab-case and not cryptic. Severity: warning.
- **K-DESC** — frontmatter `description` includes trigger language ("Use when", "Use for",
  "Auto-activates"). Severity: warning.

- **0–2**: Description is generic or missing trigger language
- **3–4**: Capability described but no explicit "Use when" triggers
- **5–6**: Some trigger phrases but overlaps with adjacent skills or too broad/narrow
- **7–8**: Specific triggers; kebab-case name; covers main activation paths
- **9–10**: Unique activation context; phrasing variants covered; no neighbor overlap

## 8. Progressive Disclosure

Body length fits the skill's scope; rare detail lives in sibling reference files.

Lint rules:

- **K-PROGRESSIVE** — skill body over 220 lines with no sibling support files. Severity: warning.
- **I-ONE-QUESTION** — interactive skills instruct one-question-at-a-time. Severity: warning.

- **0–2**: Monolithic 300+ line body with embedded reference material; OR trivial skill padded to 100+ lines
- **3–4**: 220–300 lines with detail that could be split
- **5–6**: 150–220 lines; borderline; reference material inlined instead of linked
- **7–8**: Body under 150 lines (agents) / 180 lines (skills); clear pointers to sibling files
- **9–10**: Focused workflow body; all rare/reference detail in named sibling files with conditional read instructions
