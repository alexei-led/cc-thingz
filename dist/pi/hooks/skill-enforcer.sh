#!/usr/bin/env bash
# Skill-enforcer hook - detects relevant skills from prompt and suggests activation
# Outputs minimal context only when skills detected; silent otherwise

set -euo pipefail

# Read prompt from stdin (JSON input from Claude Code)
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // .' 2>/dev/null || echo "$INPUT")
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Skip if prompt too short (likely greeting/command)
[[ ${#PROMPT_LOWER} -lt 10 ]] && exit 0

# Skip if user is already explicitly activating skills
[[ "$PROMPT_LOWER" =~ [Ss]kill\( ]] && exit 0

# Skip common follow-up patterns
[[ "$PROMPT_LOWER" =~ ^(yes|no|ok|okay|sure|thanks|continue|proceed|go\ ahead|do\ it|looks\ good|lgtm)$ ]] && exit 0

skills=""

# writing-go: Idiomatic Go development
# Triggers: .go files, go commands, Go-specific terms
if echo "$PROMPT_LOWER" | grep -qE '\.go\b|go\.(mod|sum)|go (test|build|run|fmt|vet|mod|get|generate)|golangci|mockery|\bgolang\b|\bgoroutines?\b|\bchannel\b|\bdefer\b.*func|urfave|testify|cobra/|idiomatic go|in go\b|go (code|project|package|module|interface|struct)|write.*go|implement.*go|\berror\s*handling\b.*go'; then
	skills+="writing-go "
fi

# writing-python: Idiomatic Python 3.12+ development
# Triggers: .py files, Python commands, Python frameworks
if echo "$PROMPT_LOWER" | grep -qE '\.pyi?\b|pyproject|requirements\.txt|setup\.py|__init__|python[3]?\b|\buv (run|pip|sync|add|lock)|\bruff\b|pytest|poetry\b|mypy\b|django|flask|fastapi|pandas|numpy|pydantic|dataclass|type\s*hint|\btyping\b|asyncio|\basync\b.*\bawait\b|pip install|write.*python|implement.*python'; then
	skills+="writing-python "
fi

# writing-typescript: TypeScript development with strict typing
# Triggers: .ts files, TypeScript commands, Node.js/React/Bun
if echo "$PROMPT_LOWER" | grep -qE '\.(ts|tsx)\b|typescript|tsconfig|package\.json|\bnpm\b|\bbun\b|\byarn\b|\bvite\b|react|next\.?js|node\.?js|\bexpress\b|\best\b|vitest|jest|eslint|prettier|write.*typescript|implement.*ts|strict typing'; then
	skills+="writing-typescript "
fi

# operating-infra: IaC, Kubernetes, cloud resources, containers, CI/CD, Linux hosts
# Triggers: infra files/tools, cloud services, IAM, logs, instances, service health
if echo "$PROMPT_LOWER" | grep -qE '\.tf\b|\.tfvars|dockerfile|docker-compose|chart\.yaml|kustomization|values\.yaml|\bkubectl\b|\bhelm\b|\bkustomize\b|\bterraform\b|\btofu\b|kubernetes|k8s\b|\bpod[s]?\b|\bdeployment[s]?\b|\bingress\b|\bconfigmap|\bnamespace[s]?\b|\bstatefulset|\bdaemonset|cronjob|\bhpa\b|networkpolic|manifest|container.*(image|registry|port)|service\s*account|node\s*pool|github.*action|\.github/workflows|workflow.*yaml|\bgcloud\b|\bgsutil\b|\bbq\s|\baws\s|bigquery|cloud\s*(run|function|sql|storage)|gke\b|gcs\b|pubsub|dataflow|firestore|spanner|\bs3\b|\bec2\b|aws.*lambda|lambda.*(function|handler)|\becs\b|\beks\b|\brds\b|dynamodb|\bsqs\b|\bsns\b|cloudformation|cloudwatch|iam.*(role|policy|permission)|\bbucket[s]?\b|--project\b|--region\b|systemctl|journalctl|\bnginx\b|\blinux\s*(host|service|instance)'; then
	skills+="operating-infra "
fi

# looking-up-docs: docs lookup flow (Context7 → official sources → Perplexity/web → GitHub)
# Triggers: ctx7/context7, library IDs, natural-language doc-seeking, API reference, or latest-behavior needs.
# NOT for comparisons/best-practices (use researching-web).
if echo "$PROMPT_LOWER" | grep -qE '\bctx7\b|\bcontext7\b|context7[[:space:]-]cli|/[a-z0-9._-]+/[a-z0-9._-]+\s+(library|docs|version)|\bdocs\b|\bdocumentation\b|api\s*(reference|docs)|look\s*up.*(docs|api|syntax|usage|reference|examples)|find.*(docs|documentation|reference)|check.*(docs|documentation)|man\s*page|reference.*(guide|manual)|official.*(docs|documentation)|library.*docs|version.*specific|syntax\s*for|examples\s*of|how\s*to\s*use\s*\w+'; then
	# Exclude comparison/research patterns — those go to researching-web
	if ! echo "$PROMPT_LOWER" | grep -qE '\bvs\b|\bcompare\b|\bbest\s*practice\b|\bpros\s*(and|&)\s*cons\b|\bwhich.*(better|should)\b'; then
		skills+="looking-up-docs "
	fi
fi

# researching-web: Web research via Perplexity AI (comparisons, best practices, standards)
# Triggers: Research language, comparisons, best practices, industry standards
# NOT for API references or library docs (use looking-up-docs)
if echo "$PROMPT_LOWER" | grep -qE '\bresearch\b|search.*(web|online)|look\s*up.*online|find\s*out.*(about|if|whether)|compare.*(tool|lib|framework|approach|option|technolog)|(\w+)\s+vs\s+(\w+)|pros\s*(and|&)\s*cons|trade[[:space:]-]?off|which.*(better|should|recommend)|latest.*(version|release|update)|current.*(version|best)|what.?s\s*new\s*in|best\s*practice|up[[:space:]-]?to[[:space:]-]?date|2024|2025|2026|industry\s*standard|owasp|recommended\s*(practice|approach|pattern)|perplexity'; then
	skills+="researching-web "
fi

# using-git-worktrees: Isolated git worktree management
# Triggers: Explicit worktree or isolation intent for feature work
if echo "$PROMPT_LOWER" | grep -qE 'worktree|git\s*worktree|isolat.*(work|branch|develop|implement|environment)|separate.*(workspace|environment|branch)|parallel.*(branch|work|develop)|work.*(multiple|parallel).*branch|fresh.*(workspace|environment|branch)|feature.*isolation'; then
	skills+="using-git-worktrees "
fi

# cleanup-git: Remove merged/gone branches and stale worktrees
# Triggers: cleanup branches, prune worktrees, tidy local git state
if echo "$PROMPT_LOWER" | grep -qE 'cleanup.*(git|branch|worktree)|clean\s+up.*(git|branch|worktree)|prune.*(branch|worktree|git)|tidy.*git|remove.*merged.*branch|delete.*merged.*branch|gone\s+branches|stale\s+worktrees'; then
	skills+="cleanup-git "
fi

# configuring-git-hygiene: Git hooks, Gitleaks, .gitignore, and git config hygiene
# Triggers: setup git hooks, pre-commit/pre-push, gitleaks, gitignore, git config
if echo "$PROMPT_LOWER" | grep -qE 'git[[:space:]-]?(hygiene|guardrails)|pre[[:space:]-]?commit|pre[[:space:]-]?push|gitleaks|git[[:space:]-]?leaks|secret\s+scan.*git|git\s+hooks?|core\.hooksPath|hooksPath|\.gitignore|gitignore|git\s+config.*(best|setup|hygiene|sign|pull|prune|includeif)'; then
	skills+="configuring-git-hygiene "
fi

# refactoring-code: Fast batch refactoring via MorphLLM edit_file
# Triggers: Multi-file batch changes, style updates everywhere, complex prompt → many changes
if echo "$PROMPT_LOWER" | grep -qE 'refactor.*(across|multiple|batch|all|every)|batch.*(edit|rename|update|change)|rename.*(across|everywhere|all|every)|update.*(pattern|import|style).*everywhere|(multi[[:space:]-]?file|cross[[:space:]-]?file).*(refactor|update|change)|morphllm|edit_file|5\+?\s*files|same\s*pattern.*files|style.*every'; then
	skills+="refactoring-code "
fi

# reviewing-code: Multi-agent code review for security, quality, line-level concerns
# Triggers: review code, check code, review changes, review PR
# NOT for architecture deepening
# NOT for config/setup/skills/agents/hooks review (use evolving-config)
if echo "$PROMPT_LOWER" | grep -qE '\breview\b.*\b(code|changes|this|my|the)\b|\bcode\s*review\b|\bcheck\s*(this|my|the)?\s*code\b|\bdeep\s*(code\s*)?review\b|\bfeedback\s*(on)?\s*(my|the|this)?\s*code\b|review\s*(my|the|these)?\s*(changes|implementation|pr)\b|critique\s*(my|the|this)?\s*code|find\s*line[[:space:]-]?level\s*refactoring\s*opportunities'; then
	# Exclude config-review patterns — those go to evolving-config
	if ! echo "$PROMPT_LOWER" | grep -qE '\b(config|configuration|setup|skills?|agents?|hooks?|claude\.?md)\b'; then
		skills+="reviewing-code "
	fi
fi

# committing-code: Smart git commits with logical grouping
# Triggers: commit, save changes, create commit, bundle commits
if echo "$PROMPT_LOWER" | grep -qE '\bcommit\b|\bsave\s*(my|the)?\s*changes\b|\bcreate\s*(a\s*)?commit\b|\bbundle\s*commits?\b|\bgit\s*commit\b|\bcommit\s*(my|the|these)?\s*(changes|work|code)\b|\bsave\s*(my)?\s*work\b'; then
	skills+="committing-code "
fi

# fixing-code: Fix issues via diagnosis and verification
# Triggers: fix/debug/diagnose/repro issues, errors, bugs, lint, tests, performance regressions
if echo "$PROMPT_LOWER" | grep -qE '\bfix\s*(all|the|my|these|this|any)?\s*(issue|error|bug|problem|warning|lint|test|failure|type\s*error|build|compilation)s?\b|\bfix\s*(it|this|them|everything)\b|\bresolve\s*(the|all|these)?\s*(issue|error|bug)s?\b|\baddress\s*(the|all)?\s*(issue|error|warning)s?\b|make\s*(it|the|tests?|build)\s*(pass|work|green)\b|\bdebug\b|\bdiagnos(e|is)\b|\brepro(duce)?\b|\bperformance\s*regression\b|\bthrow(s|ing)?\b|\bcrash(es|ing)?\b|\bbroken\b'; then
	skills+="fixing-code "
fi

# documenting-code: Update documentation based on changes
# Triggers: update docs, document, add documentation, update readme, write docs
if echo "$PROMPT_LOWER" | grep -qE '\bupdate\s*(the|my)?\s*(docs|documentation|readme)\b|\bdocument\s*(this|the|my|these)?\s*(code|changes|function|api)?\b|\badd\s*(some|more)?\s*documentation\b|\bwrite\s*(the|some)?\s*docs\b|\bimprove\s*(the)?\s*documentation\b|\bdocstring|\bjsdoc\b|\bgodoc\b'; then
	skills+="documenting-code "
fi

# deploying-infra: Validate and deploy K8s, Terraform, Helm, GitHub Actions, Docker configs
# Triggers: deploy check, validate deployment, deploy to staging, terraform apply, helm upgrade, kubectl apply, rollout
if echo "$PROMPT_LOWER" | grep -qE '\bdeploy\s*check\b|\bcheck\s*(my|the)?\s*deploy(ment)?\b|\bvalidate\s*(my|the)?\s*(deployment|infrastructure|infra|k8s|kubernetes|helm|terraform|config)s?\b|\bcheck\s*(my|the)?\s*(k8s|kubernetes|helm|terraform|workflow|action)\s*(config|manifest|file)s?\b|\bverify\s*(the)?\s*infrastructure\b|\binfra\s*check\b|\bdeploy\s*to\s|apply\s*(the\s*)?(changes|infra)|terraform\s*apply|helm\s*(upgrade|install)|kubectl\s*apply|rollout'; then
	skills+="deploying-infra "
fi

# browser-automation: Browser exploration, validation, screenshots, and UI-flow tests
# Triggers: browser exploration/checks, screenshots, UI automation, E2E, Playwright
if echo "$PROMPT_LOWER" | grep -qE '\be2e\b.*\btest|\bplaywright\b|\bbrowser\s*(test|testing|automation|check|validation|verify|verification|exploration|inspect|debug|screenshot|record)\b|\b(use|open|drive|inspect|explore|validate|verify|record|screenshot|capture)\s*(a\s*)?(real\s*)?browser\b|\bscreenshot\b|\bui\s*(test|testing|automation|check|validation|verification|debug)\b|\brendered\s*(dom|page|state|ui)\b|\bend[[:space:]-]?to[[:space:]-]?end\b|\bvisual\s*(test|testing|check|regression|diff)\b|\baccessibility\s*(test|testing|check|audit)\b|\ba11y\s*(test|check|audit)\b'; then
	skills+="browser-automation "
fi

# writing-web: Simple web development with HTML, CSS, JS, HTMX
# Triggers: HTML, CSS, JS, web template, stylesheet, HTMX
# NOT for React/Vue/Angular/Node.js (use writing-typescript)
if echo "$PROMPT_LOWER" | grep -qE '\bhtml\s*(template|file|page|component)?\b|\bcss\s*(style|file|class)?\b|\bstylesheet\b|\bhtmx\b|\bweb\s*(template|page|component|form)\b|\bhtml\s*and\s*css\b|\bvanilla\s*js\b|\bdom\s*manipulat|\.html\b|\.css\b'; then
	# Exclude React/Vue/Angular/Node — those go to writing-typescript
	if ! echo "$PROMPT_LOWER" | grep -qE '\breact\b|\bvue\b|\bangular\b|\bnext\.?js\b|\bnode\.?js\b|\btsx\b'; then
		skills+="writing-web "
	fi
fi

# brainstorming-ideas: Brainstorm ideas and stress-test draft plans
# Triggers: brainstorm/design, plan exploration, resolve design-blocking terms
# Also owns the "grill me" decision-tree interview (see grill block below)
if echo "$PROMPT_LOWER" | grep -qE '\bbrainstorm\b|\bideate\b|\bdesign\s*(a|an|this|the|new)?\s*(\w+\s+)?(feature|component|system|api|flow|architecture)\b|\bexplore\s*(approach|option|idea|design|alternative)s?\b|\bthink\s*through\b|\bbefore\s*(i|we)?\s*(implement|code|build|start)\b|\bplan\s*(out|this|the)?\s*(feature|design|approach)\b|\bsketch\s*out\b|\bfigure\s*out\s*(how|what|the)\b|\bdesign\s*session\b|\bwhat\s*should\s*(i|we)\s*(build|implement|create)\b|\bCONTEXT\.md\b|\bADR\b|domain\s*(language|glossary|term)'; then
	skills+="brainstorming-ideas "
fi

# brainstorming-ideas (grill/debate): decision-tree interview on a bounded plan/design
# Triggers: "grill me", debate/pros-cons, stress-test a specific plan, challenge an existing design
if echo "$PROMPT_LOWER" | grep -qE '\bgrill\s*(me|this|the|my)\b|\bdebate\b|\bargue\s*(both)?\s*sides\b|\bdevil.?s?\s*advocate\b|\bpros\s*(and|&)\s*cons\b|\bstress[[:space:]-]?test\s*(this|the|my|an?)?\s*(plan|design|idea|approach|decision|claim)\b|\bchallenge\s+me\b|\bchallenge\s*(this|the|my)?\s*(plan|design|idea|approach|assumption)\b|\binterview\s*me\b.*\b(plan|design|approach)\b'; then
	skills+="brainstorming-ideas "
fi

# writing-shell: POSIX sh, Bash, Zsh, Fish, hooks, CI shell steps, shell tests
# Triggers: shell scripts, pipelines, shell lint/test tools, portable CLI glue
if echo "$PROMPT_LOWER" | grep -qE '\.(sh|bash|zsh|fish|bats)\b|\b(shell|bash|zsh|fish)\s*(script|function|pipeline|hook|config)\b|shebang|pipefail|shellcheck|shfmt|checkbashisms|bats(-core|-assert)?|shellspec|bashate|shellharden|shellcheck-sarif|semgrep.*shell|\b(posix|portable)\s*sh\b|\b(command|cli)\s*(pipeline|chain|runner|glue)\b|scriptable.*cli|pipe.?friendly|better\s*than\s*(grep|find|cat|sed|ls|du|ps|diff|curl|time|df|awk|cut)|replace.*(grep|find|cat|sed|ls|du|ps|diff|curl|time|df|awk|cut)'; then
	skills+="writing-shell "
fi

# improving-tests: Review, refactor, improve tests, and TDD workflow
# Triggers: improve tests, refactor tests, coverage, TDD, red-green-refactor
if echo "$PROMPT_LOWER" | grep -qE '\bimprove\s*(my|the|these)?\s*tests?\b|\brefactor\s*(my|the|these)?\s*tests?\b|\btest\s*coverage\b|\bcombine\s*(the|my)?\s*tests?\b|\btable[[:space:]-]?driven\b|\bparametri[sz]e\b|\btest\.each\b|\beliminate\s*test\s*waste\b|\btest\s*(quality|improvement|cleanup)\b|\btdd\b|test[[:space:]-]?first|red[[:space:]-]?green[[:space:]-]?refactor|write\s*(the\s*)?test\s*first'; then
	skills+="improving-tests "
fi

# spec-status: Progress overview + orientation for spec-driven projects
# Triggers: project status, progress, how far along, spec status,
#           how does spec work, spec guide, spec methodology, spec workflow
if echo "$PROMPT_LOWER" | grep -qE '\b(project|spec|task)\s*(status|progress|overview)\b|\bhow\s*(far|much|many|is)\s*(along|done|progress|left|remain|complete)\b|\bwhat.*(done|left|remain|progress|status)\b|\bshow\s*(me\s*)?(progress|status|overview)\b|\bhow.*project\s*(going|doing)\b|\bhow\s*does\s*spec\b|\bspec\s*(guide|help|methodology|workflow|reference)\b|\bspec[[:space:]-]driven\s*(guide|help|how)\b|\bwhat\s*(are|is)\s*(the)?\s*spec\s*(command|workflow|phase|skill)'; then
	skills+="spec-status "
fi

# spec-init: Initialize .spec/ project structure
# Triggers: init spec, set up spec, new spec project, start spec
if echo "$PROMPT_LOWER" | grep -qE '\bspec[[:space:]-]?init\b|\b(init|initialize|setup|set[[:space:]-]up)\s*(a\s*)?spec\b|\bnew\s*spec\s*(project|folder|dir)\b|\bstart\s*(spec[[:space:]-]driven|a\s*spec)\b'; then
	skills+="spec-init "
fi

# spec-interview: Requirement extraction with domain/out-of-scope context
# Triggers: gather requirements, PRD, interview, out-of-scope triage
if echo "$PROMPT_LOWER" | grep -qE '\b(requirements?|prd|product\s*requirements?)\b|spec[[:space:]-]?interview|interview\s*(me|for|about)|out[[:space:]-]?of[[:space:]-]?scope|triage\s*(issue|request|feature)'; then
	skills+="spec-interview "
fi

# spec-plan: Create vertical-slice task plan
# Triggers: implementation plan, break into tasks/issues, vertical slices
if echo "$PROMPT_LOWER" | grep -qE 'spec[[:space:]-]?plan|implementation\s*plan|break\s*(this|it)?\s*(into)?\s*(tasks|issues|tickets)|vertical\s*slice|tracer\s*bullet|create\s*(tasks|issues)'; then
	# Plan review/grilling belongs to brainstorming-ideas, not task generation.
	if ! echo "$PROMPT_LOWER" | grep -qE '\b(grill|stress[[:space:]-]?test|challenge|review)\b.*\bplan\b|\bplan\b.*\b(grill|stress[[:space:]-]?test|challenge|review)\b'; then
		skills+="spec-plan "
	fi
fi

# spec-new: Create a single task or requirement from a template
# Triggers: new task, new req, add a task, create task file
if echo "$PROMPT_LOWER" | grep -qE '\b(new|add|create)\s*(a\s*)?(spec\s*)?(task|req|requirement)\b|spec[[:space:]-]?new\b|\badd\s*(a\s*)?task\s*to\s*spec\b'; then
	skills+="spec-new "
fi

# spec-work: Main workflow - select, plan, implement, verify
# Triggers: start/continue spec work, next task
if echo "$PROMPT_LOWER" | grep -qE '\b(start|begin|continue|resume)\s*(spec\s*)?(work|task|implementation)\b|\bnext\s*(ready\s*)?(task|work)\b|\bwork\s*on\s*(the\s*)?(next|a)\s*task\b|\bspec[[:space:]-]?work\b|\bpick\s*up\s*(a\s*)?(new\s*)?task\b'; then
	skills+="spec-work "
fi

# spec-done: Mark a task complete with evidence
# Triggers: mark done, task complete, close task, finish task
if echo "$PROMPT_LOWER" | grep -qE '\b(mark|close|finish|complete)\s*(a\s*)?(spec\s*)?(task|ticket)\b|\btask\s*(done|complete|finished|closed)\b|spec[[:space:]-]?done\b|\bmark.*done\b'; then
	skills+="spec-done "
fi

# sequential-thinking: Externalized stepwise reasoning with revisions and branches
# Triggers: explicit "step by step" / "sequential thinking" / revise-and-branch language
# NOT for "think through" or "stress test" (brainstorming-ideas)
if echo "$PROMPT_LOWER" | grep -qE '\bsequential[[:space:]-]?thinking\b|\bstep[[:space:]-]?by[[:space:]-]?step\b|\breason\s*through\s*(this|it|the)\b|\bplan\s*(this|it)\s*out\b|\bwalk\s*(me\s*)?through\s*(this|the|your)?\s*reasoning\b|\bbranch\s*(this|the|an?)\s*(idea|approach|reasoning|thought)\b|\brevise\s*(my|the|your)?\s*(reasoning|thought|earlier\s*step)\b|\bnumbered\s*thoughts?\b|\bshow\s*(your|the)?\s*reasoning\s*steps?\b'; then
	skills+="sequential-thinking "
fi

# evolving-config: Audit Claude Code config against latest features
# Triggers: evolve, self-improve, audit config, what's new in claude code
if echo "$PROMPT_LOWER" | grep -qE '\bevolve\b|\bself[[:space:]-]?improv\b|\baudit\s*(my|the)?\s*(config|configuration|settings|setup)\b|\bwhat.?s\s*new\s*in\s*claude\s*code\b|\bupgrade\s*(my|the)?\s*(config|configuration|settings)\b|\bcheck\s*(for)?\s*(improvement|update)s?\b|\bare\s*(we|my\s*settings?)\s*up[[:space:]-]?to[[:space:]-]?date\b|\blatest\s*(claude|features)\b|\bimprove\s*(my|the)?\s*(claude|config|setup)\b'; then
	skills+="evolving-config "
fi

# evolving-config: Audit and improve agent configuration across platforms; supports review-only audits and apply-fixes mode

# reviewing-instructions: Review and score AI agent/skill instructions for quality
# Triggers: reviewing/linting/scoring skills, agents, SKILL.md, AGENTS.md, CLAUDE.md, instruction files
if echo "$PROMPT_LOWER" | grep -qE '\b(lint|audit|review|score|check)\s+(the\s+|my\s+|this\s+|all\s+|a\s+)?(skill|agent|plugin|instruction|prompt)s?\b|\b(reviewing|auditing|scoring)[- ]instructions\b|\b(skill|agent|instruction|prompt)\s*(quality|score|audit|review|lint)\b|\breview\s+\S*(skill\.md|agents?\.md|claude\.md)\b|\bsignal\s+density\b|\bfluff\s+(meter|score)\b|\bprompt\s*(quality|lint|audit|review|score)\b|\binstruction\s*(quality|lint|audit|review|score)\b|\bmodel\s*card\s*(lint|review|check|rules?)\b'; then
	skills+="reviewing-instructions "
fi

# Output only if skills detected (silent when no match)
if [[ -n "$skills" ]]; then
	skills="${skills% }"
	echo "→ Consider skills: $skills"
fi
# Silent exit when no skills detected - reduces context noise
