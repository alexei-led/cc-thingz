.DEFAULT_GOAL := help

NODE_VERSION ?= $(shell cat .node-version 2>/dev/null || echo 24)
SKILL_EVAL_ROOT ?= /tmp/cc-thingz-skill-eval-root
SKILL_EVAL_WORKSPACE ?= /tmp/cc-thingz-skill-eval-workspace
SKILL_EVAL_INCLUDE ?= **
SKILL_EVAL_SOURCE ?= skills
SKILL_EVAL_TARGET ?= gpt-5.4-mini
SKILL_EVAL_JUDGE ?= gpt-5.4-mini
SKILL_EVAL_LOG_FORMAT ?= jsonl
SKILL_EVAL_LOG_FILE ?= $(SKILL_EVAL_WORKSPACE)/events.jsonl
SKILL_EVAL_REPORT ?= $(SKILL_EVAL_WORKSPACE)/summary.md
SKILL_EVAL_HTML_REPORT ?= 1
SKILL_EVAL_BASELINE ?= 1
SKILL_EVAL_CONCURRENCY ?= 4
SKILL_EVAL_STRICT ?= 1
SKILL_EVAL_CLI ?= $(shell if command -v agent-skills-eval >/dev/null 2>&1; then printf 'agent-skills-eval'; elif command -v bunx >/dev/null 2>&1; then printf 'bunx agent-skills-eval'; elif command -v fnm >/dev/null 2>&1; then printf 'fnm exec --using $(NODE_VERSION) -- npx --yes agent-skills-eval'; else printf 'npx --yes agent-skills-eval'; fi)

# --- Lint ---

.PHONY: lint lint-python lint-shell lint-markdown lint-typescript
lint: lint-python lint-shell lint-markdown lint-typescript ## Run all linters

lint-python: ## Lint Python files with ruff
	uv run ruff check .
	uv run ruff format --check .

lint-shell: ## Lint shell scripts with shellcheck + shfmt (matches CI's action-sh-checker scope)
	@command -v shellcheck >/dev/null 2>&1 || { echo "shellcheck not installed"; exit 1; }
	@command -v shfmt >/dev/null 2>&1 || { echo "shfmt not installed"; exit 1; }
	find src scripts -name '*.sh' -exec shellcheck {} +
	find src scripts -name '*.sh' -exec shfmt -i 0 -d {} +
	@# Cover .bats test files and extension-less shell scripts CI also lints
	find tests -name '*.bats' -exec shfmt -i 0 -d {} +
	shfmt -i 0 -d scripts/git-hooks/pre-commit scripts/git-hooks/pre-push scripts/release/release-tag

lint-markdown: ## Lint Markdown files
	@command -v markdownlint-cli2 >/dev/null 2>&1 || { echo "markdownlint-cli2 not installed — skipping"; exit 0; }
	markdownlint-cli2 '**/*.md' '!node_modules/**' '!.pi-subagents/**'

lint-typescript: ## Type-check Pi extension TypeScript
	bun x tsc --noEmit

# --- Test ---

.PHONY: test test-ts skill-evals-prepare skill-evals skill-evals-fast skill-evals-both skill-evals-summary
test: ## Run pytest suite
	uv run --extra test python -m pytest tests/ -v

test-ts: ## Run Bun TypeScript tests (Pi extensions)
	bun test src/pi-extensions --isolate

skill-evals-prepare: ## Build temporary Agent Skills eval tree under /tmp
	uv run python scripts/evals/prepare-skill-evals.py --out $(SKILL_EVAL_ROOT) --source-dir $(SKILL_EVAL_SOURCE)

skill-evals: skill-evals-prepare ## Run paid Agent Skills evals and print fix-focused summary
	@set -u; \
	if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	test -n "$${OPENAI_API_KEY:-}" || { echo "OPENAI_API_KEY missing"; exit 2; }; \
	mkdir -p $(SKILL_EVAL_WORKSPACE); \
	baseline_flag=""; \
	if [ "$(SKILL_EVAL_BASELINE)" != "0" ]; then baseline_flag="--baseline"; fi; \
	report_flag="--no-report"; \
	if [ "$(SKILL_EVAL_HTML_REPORT)" != "0" ]; then report_flag="--report"; fi; \
	$(SKILL_EVAL_CLI) $(SKILL_EVAL_ROOT) \
		--include '$(SKILL_EVAL_INCLUDE)' \
		--workspace $(SKILL_EVAL_WORKSPACE) \
		$$baseline_flag \
		--target $(SKILL_EVAL_TARGET) \
		--judge $(SKILL_EVAL_JUDGE) \
		--base-url https://api.openai.com/v1 \
		--api-key-env OPENAI_API_KEY \
		--concurrency $(SKILL_EVAL_CONCURRENCY) \
		--log-format $(SKILL_EVAL_LOG_FORMAT) \
		--log-file $(SKILL_EVAL_LOG_FILE) \
		--layout iteration \
		--strict \
		$$report_flag; \
	status=$$?; \
	uv run python scripts/evals/summarize-skill-evals.py $(SKILL_EVAL_WORKSPACE) --markdown $(SKILL_EVAL_REPORT) || true; \
	if [ "$(SKILL_EVAL_STRICT)" = "0" ]; then exit 0; fi; \
	exit $$status

skill-evals-fast: ## Fast paid skill eval loop: no baseline, no HTML, higher concurrency, advisory
	$(MAKE) skill-evals SKILL_EVAL_BASELINE=0 SKILL_EVAL_HTML_REPORT=0 SKILL_EVAL_CONCURRENCY=8 SKILL_EVAL_STRICT=0

skill-evals-both: ## Run source and Codex/Gemini overlay evals in parallel with separate workspaces
	@set +e; \
	$(MAKE) skill-evals SKILL_EVAL_SOURCE=skills SKILL_EVAL_ROOT=/tmp/cc-thingz-skill-eval-root-source SKILL_EVAL_WORKSPACE=/tmp/cc-thingz-skill-eval-workspace-source SKILL_EVAL_LOG_FILE=/tmp/cc-thingz-skill-eval-workspace-source/events.jsonl SKILL_EVAL_REPORT=/tmp/cc-thingz-skill-eval-workspace-source/summary.md SKILL_EVAL_STRICT=0 & \
	pid1=$$!; \
	$(MAKE) skill-evals SKILL_EVAL_SOURCE=skills-codex SKILL_EVAL_ROOT=/tmp/cc-thingz-skill-eval-root-codex SKILL_EVAL_WORKSPACE=/tmp/cc-thingz-skill-eval-workspace-codex SKILL_EVAL_LOG_FILE=/tmp/cc-thingz-skill-eval-workspace-codex/events.jsonl SKILL_EVAL_REPORT=/tmp/cc-thingz-skill-eval-workspace-codex/summary.md SKILL_EVAL_STRICT=0 & \
	pid2=$$!; \
	wait $$pid1; status1=$$?; \
	wait $$pid2; status2=$$?; \
	[ $$status1 -eq 0 ] && [ $$status2 -eq 0 ]

skill-evals-summary: ## Print summary for latest skill eval workspace
	uv run python scripts/evals/summarize-skill-evals.py $(SKILL_EVAL_WORKSPACE) --markdown $(SKILL_EVAL_REPORT)

# --- Validate ---

# `make build` regenerates every derived artifact idempotently and `make check`
# fails if anything diverges from canonical sources. Per-artifact --check
# targets are gone — they duplicated what `make check` already proves
# end-to-end, and disagreed with each other when generators changed.

.PHONY: validate validate-config validate-executables validate-genericity lint-instructions
validate: validate-config validate-genericity validate-executables ## Validate canonical sources (frontmatter, executable bits, plugin layout)

validate-config: ## Validate plugin configs and frontmatter
	uv run python scripts/validate/validate-config.py

validate-genericity: ## Reject Claude-only tokens in vendor-neutral base SKILL.md/AGENT.md
	uv run python scripts/validate/validate_genericity.py

lint-instructions: ## Lint agent/skill instructions (advisory)
	@uv run python src/skills/reviewing-instructions/scripts/lint-instructions.py

validate-executables: ## Check shell + Python entry scripts have executable bit
	@fail=0; \
	for f in $$(find src -name 'hook.py' -type f) \
		$$(find src scripts -name '*.sh') \
		scripts/git-hooks/pre-commit scripts/git-hooks/pre-push scripts/release/release-tag; do \
		[ -x "$$f" ] || { echo "ERROR: $$f is not executable"; fail=1; }; \
	done; \
	[ $$fail -eq 0 ] || exit 1

# --- Format ---

.PHONY: fmt
fmt: ## Auto-format Python and shell files
	uv run ruff check --fix .
	uv run ruff format .
	find src scripts -name '*.sh' -exec shfmt -i 0 -w {} +
	shfmt -i 0 -w scripts/git-hooks/pre-commit scripts/git-hooks/pre-push scripts/release/release-tag

# --- One-shot build: regenerate everything derived from canonical sources ---

.PHONY: build check
build: ## Regenerate dist/ and root manifests from canonical sources under src/
	uv run python scripts/build/compile.py

check: build ## Build, then fail if any tracked file changed (drift detection)
	@if ! git diff --quiet --exit-code; then \
		echo "ERROR: derived artifacts drifted. See diff above for either updated sources or hand-edited generated files."; \
		echo "  Hand-edits to generated files are overwritten by 'make build' — edit canonical sources under src/ instead."; \
		git --no-pager diff --stat; \
		exit 1; \
	fi
	@untracked=$$(git ls-files --others --exclude-standard -- dist/ .claude-plugin/ .agents/plugins/ gemini-extension.json); \
	if [ -n "$$untracked" ]; then \
		echo "ERROR: build produced untracked derived files — add them or remove a stale src/ entry:"; \
		echo "$$untracked" | sed 's/^/  /'; \
		exit 1; \
	fi
	@echo "check: clean (all derived artifacts match canonical sources)"

# --- CI (runs everything) ---

.PHONY: ci
ci: lint validate check test test-ts ## Run full CI pipeline locally (lint + validate + build & check drift + tests)

# --- Setup ---

.PHONY: setup
setup: ## Install repo-tracked git hooks (pre-commit + pre-push) and dev deps
	git config core.hooksPath scripts/git-hooks
	uv sync --extra test
	@echo "Setup complete — git hooks active via core.hooksPath=scripts/git-hooks"

# --- Push ---

.PHONY: push
push: ## Push master to origin and all private mirrors (CI rewrites manifests)
	git push origin master
	git push cc-forge master:main --force-with-lease

# --- Release ---

.PHONY: release
release: ## Create release tag (usage: make release V=1.2.0)
ifndef V
	$(error Usage: make release V=1.2.0)
endif
	scripts/release/release-tag v$(V)
	@echo "Push with: git push origin master v$(V)"

# --- Help ---

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
