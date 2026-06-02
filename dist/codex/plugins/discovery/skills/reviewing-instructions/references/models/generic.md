# Generic LLM Context

Applies when no specific model is identified. Covers universal best practices that hold across frontier LLMs (Claude, GPT, Gemini, Llama, etc.).

## Universal instruction principles

- **Specificity** is the strongest performance predictor: +15–20% zero-shot improvement over generic instructions (PromptBench).
- **Structure** (numbered steps, `#` headers, code blocks) improves instruction following across all models. XML-tagged sections add +5–15%.
- **Verbosity hurts**: minimal zero-shot outperforms verbose few-shot on recall. Over-specifying past ~200 lines causes rule amnesia.
- **Grounding**: ReAct-style tool grounding reduces hallucination ~30%. Explicitly require evidence-anchored outputs.
- **Failure handling**: without explicit failure vocabulary, models fabricate workarounds or hallucinate success.
- **Output format**: define a concrete template — models pattern-match well against structure; prose descriptions of format are less reliable.

## Rules to apply

All rules are in `references/scoring-rubric.md`. Apply universal (U-prefix), format (F-prefix), and skill-structure (K-prefix) rules. Do NOT apply Opus-specific (O-prefix) or Sonnet-specific (S-prefix) rules — those are Claude-only.

## When to fetch model docs

If the instruction file targets a specific model and no reference file exists in `references/models/`, use available web tools to read the vendor's prompting guide and extract:

1. Documented behavioral quirks (over-exploration, verbosity, lecture tendency, etc.)
2. Recommended prompt structure (system/user format, XML tags, markdown conventions)
3. Token efficiency guidance
4. Any safety or refusal patterns to account for in failure-handling instructions
