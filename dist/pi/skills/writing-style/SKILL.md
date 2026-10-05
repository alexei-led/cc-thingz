---
{"description":"Write or edit commit messages, PR/MR descriptions, issues, review comments, and technical discussions. Use for concise, clear engineering communication grounded in facts, without filler or boilerplate. NOT for creating commits (committing-code), project docs (documenting-code), release notes (releasing-code), or AI instructions (writing-skills).\n","name":"writing-style"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Read required skill/instruction files through direct read when exposed or through Code Mode. If an optional pruning extension is installed, verify its output protection semantics; do not assume nested-path protection. Code Mode composes calls; subagents or controllers own durable workflows. Async subagents notify natively: yield rather than poll. -->


# Writing Style

Produce text that a reader understands in one pass, with the fewest words that
preserve its meaning. Explicit user and project requirements override these
defaults. Apply the style in the reader's language, not just English.

Done when the text states the concrete point, contains no redundant material,
and preserves necessary context, risks, and uncertainty. Return the text itself
unless the user asks for an explanation or review.

## Clarity

- Lead with the result, problem, decision, or request. Each sentence adds a
  fact, reason, or action.
- Use one term per concept. Name the actor and referent; expand unfamiliar
  abbreviations. Give enough context to understand the note without chat history.
- Prefer actions to abstract nouns: "validate input", not "perform validation".
- Replace quality claims with evidence or remove them. State recommendations
  directly, but label unverified claims and genuine uncertainty.
- Cut ceremonial openings, repeated questions, process narration, sign-offs,
  and empty headings. Keep grammatical sentences; brevity is not shorthand.
- Preserve negation, conditions, compatibility limits, security risks, required
  migrations, and project-mandated trailers or templates.
- Leave code, identifiers, commands, paths, quoted errors, and logs unchanged.

## Forms

- **Commit:** name the concrete change in the subject. Add a body only for a
  non-obvious reason, consequence, or migration. Keep the repository's format.
- **PR/MR:** explain what changed and why, then verification and remaining risks
  when relevant. A small change can take two sentences. Distinguish checks run
  from checks not run; never infer success from intent.
- **Issue:** observed behavior, expected behavior, and a minimal reproduction
  when available. Separate evidence from suspected causes.
- **Review comment:** defect, consequence, and a concrete fix or question.
  Cite the affected location; avoid praise sandwiches and unsupported certainty.
- **Discussion:** answer or decision first, then the reason and next action
  only when needed. Do not restate the question.

Use lists for separate points and tables for comparisons. A diagram belongs
only when it explains faster than text and the destination supports it; use
documenting-code for visual selection and render checks, not decorative charts.

## Final pass

Delete any sentence that adds no information. Check that a reader can identify
what changed, why it matters, and what remains unknown without guessing.
Retain facts that affect the reader's next action, even when the note grows.

Drafting or editing does not authorize posting, publishing, or creating a commit.
