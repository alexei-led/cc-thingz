#!/bin/bash
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

# writing-go: Idiomatic Go 1.25+ development
# Triggers: .go files, go commands, Go-specific terms
if echo "$PROMPT_LOWER" | grep -qE '\.go\b|go\.(mod|sum)|go (test|build|run|fmt|vet|mod|get|generate)|golangci|mockery|\bgolang\b|\bgoroutines?\b|\bchannel\b|\bdefer\b.*func|urfave|testify|cobra/|idiomatic go|in go\b|go (code|project|package|module|interface|struct)|write.*go|implement.*go|\berror\s*handling\b.*go'; then
	skills+="writing-go "
fi

# writing-python: Idiomatic Python 3.14+ development
# Triggers: .py files, Python commands, Python frameworks
if echo "$PROMPT_LOWER" | grep -qE '\.pyi?\b|pyproject|requirements\.txt|setup\.py|__init__|python[3]?\b|\buv (run|pip|sync|add|lock)|\bruff\b|pytest|poetry\b|mypy\b|django|flask|fastapi|pandas|numpy|pydantic|dataclass|type\s*hint|\btyping\b|asyncio|\basync\b.*\bawait\b|pip install|write.*python|implement.*python'; then
	skills+="writing-python "
fi

# writing-typescript: TypeScript development with strict typing
# Triggers: .ts files, TypeScript commands, Node.js/React/Bun
if echo "$PROMPT_LOWER" | grep -qE '\.(ts|tsx)\b|typescript|tsconfig|package\.json|\bnpm\b|\bbun\b|\byarn\b|\bvite\b|react|next\.?js|node\.?js|\bexpress\b|\best\b|vitest|jest|eslint|prettier|write.*typescript|implement.*ts|strict typing'; then
	skills+="writing-typescript "
fi

# managing-infra: K8s, Terraform, Helm, Kustomize, GitHub Actions
# Triggers: K8s resources, IaC tools, container orchestration, CI/CD
if echo "$PROMPT_LOWER" | grep -qE '\.tf\b|\.tfvars|dockerfile|docker-compose|chart\.yaml|kustomization|values\.yaml|\bkubectl\b|\bhelm\b|\bkustomize\b|\bterraform\b|kubernetes|k8s\b|\bpod[s]?\b|\bdeployment[s]?\b|\bingress\b|\bconfigmap|\bnamespace[s]?\b|\breplica[s]?\b|\bstatefulset|\bdaemonset|cronjob|\bhpa\b|networkpolic|manifest|container.*(image|registry|port)|service\s*account|node\s*pool|github.*action|\.github/workflows|workflow.*yaml'; then
	skills+="managing-infra "
fi

# using-cloud-cli: GCP/AWS cloud CLI patterns
# Triggers: Cloud provider CLIs, cloud services, BigQuery
if echo "$PROMPT_LOWER" | grep -qE '\bgcloud\b|\bgsutil\b|\bbq\s|\baws\s|bigquery|cloud\s*(run|function|sql|storage)|gke\b|gcs\b|pubsub|dataflow|firestore|spanner|\bs3\b|\bec2\b|aws.*lambda|lambda.*(function|handler)|\becs\b|\beks\b|\brds\b|dynamodb|\bsqs\b|\bsns\b|cloudformation|cloudwatch|iam.*(role|policy|permission)|\bbucket[s]?\b|--project\b|--region\b'; then
	skills+="using-cloud-cli "
fi

# looking-up-docs: Library documentation via Context7
# Triggers: Explicit doc-seeking language, API reference needs
# NOT for comparisons/best-practices (use researching-web)
if echo "$PROMPT_LOWER" | grep -qE '\bdocs\b|\bdocumentation\b|api\s*(reference|docs)|look\s*up.*(docs|api|syntax|usage|reference|examples)|find.*(docs|documentation|reference)|check.*(docs|documentation)|man\s*page|reference.*(guide|manual)|official.*(docs|documentation)|library.*docs|version.*specific|syntax\s*for|examples\s*of|how\s*to\s*use\s*\w+'; then
	# Exclude comparison/research patterns — those go to researching-web
	if ! echo "$PROMPT_LOWER" | grep -qE '\bvs\b|\bcompare\b|\bbest\s*practice\b|\bpros\s*(and|&)\s*cons\b|\bwhich.*(better|should)\b'; then
		skills+="looking-up-docs "
	fi
fi

# researching-web: Web research via Perplexity AI (comparisons, best practices, standards)
# Triggers: Research language, comparisons, best practices, industry standards
# NOT for API references or library docs (use looking-up-docs)
if echo "$PROMPT_LOWER" | grep -qE '\bresearch\b|search.*(web|online)|look\s*up.*online|find\s*out.*(about|if|whether)|compare.*(tool|lib|framework|approach|option|technolog)|(\w+)\s+vs\s+(\w+)|pros\s*(and|&)\s*cons|trade[\s-]?off|which.*(better|should|recommend)|latest.*(version|release|update)|current.*(version|best)|what.?s\s*new\s*in|best\s*practice|up[\s-]?to[\s-]?date|2024|2025|2026|industry\s*standard|owasp|recommended\s*(practice|approach|pattern)|perplexity'; then
	skills+="researching-web "
fi

# using-git-worktrees: Isolated git worktree management
# Triggers: Explicit worktree or isolation intent for feature work
if echo "$PROMPT_LOWER" | grep -qE 'worktree|git\s*worktree|isolat.*(work|branch|develop|implement|environment)|separate.*(workspace|environment|branch)|parallel.*(branch|work|develop)|work.*(multiple|parallel).*branch|clean.*(workspace|environment|slate)|fresh.*(workspace|environment|branch)|feature.*isolation'; then
	skills+="using-git-worktrees "
fi

# searching-code: Intelligent codebase search + zoom-out mapping via WarpGrep
# Triggers: Understanding code flow, tracing, cross-file exploration, zoom-out requests, large repos
# "how does X work" only for THIS codebase — external libs go to looking-up-docs/exploring-repos
if echo "$PROMPT_LOWER" | grep -qE 'how\s*does.*(this|our|the\s*(code|project|repo|module|function|class|method)).*work|trace.*(flow|data|request|call)|understand.*(codebase|code|flow|architecture)|find\s*all.*(implementation|usage|call|reference)|cross[\s-]?file|multi[\s-]?hop|where.*implemented|explore.*(codebase|code)|large\s*repo|warpgrep|intelligent\s*search|reason.*about.*code|zoom\s*out|go\s*up\s*a\s*layer|map\s*(this|the)?\s*(area|module|code|flow)|caller\s*map|module\s*map'; then
	skills+="searching-code "
fi

# refactoring-code: Fast batch refactoring via MorphLLM edit_file
# Triggers: Multi-file batch changes, style updates everywhere, complex prompt → many changes
if echo "$PROMPT_LOWER" | grep -qE 'refactor.*(across|multiple|batch|all|every)|batch.*(edit|rename|update|change)|rename.*(across|everywhere|all|every)|update.*(pattern|import|style).*everywhere|(multi[\s-]?file|cross[\s-]?file).*(refactor|update|change)|morphllm|edit_file|5\+?\s*files|same\s*pattern.*files|style.*every'; then
	skills+="refactoring-code "
fi

# reviewing-code: Multi-agent code review for security, quality, architecture
# Triggers: review code, check code, review changes, review PR, architecture/deep-module review
# NOT for config/setup/skills/agents/hooks review (use reviewing-cc-config)
if echo "$PROMPT_LOWER" | grep -qE '\breview\b.*\b(code|changes|this|my|the)\b|\bcode\s*review\b|\bcheck\s*(this|my|the)?\s*code\b|\bdeep\s*(code\s*)?review\b|\bfeedback\s*(on)?\s*(my|the|this)?\s*code\b|review\s*(my|the|these)?\s*(changes|implementation|pr)\b|critique\s*(my|the|this)?\s*code|architecture\s*review|review\s*(the\s*)?architecture|find\s*(architecture|refactoring)\s*opportunities|deep\s*module|shallow\s*module|seam|adapter\b|deletion\s*test'; then
	# Exclude config-review patterns — those go to reviewing-cc-config
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

# testing-e2e: E2E testing with Playwright MCP
# Triggers: e2e test, playwright, browser testing, UI automation
if echo "$PROMPT_LOWER" | grep -qE '\be2e\b.*\btest|\bplaywright\b|\bbrowser\s*(test|testing|automation)\b|\bui\s*(test|testing|automation)\b|\bend[\s-]?to[\s-]?end\b|\bvisual\s*(test|testing|regression)\b|\baccessibility\s*(test|testing|check)\b|\ba11y\s*(test|check)\b'; then
	skills+="testing-e2e "
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
# Triggers: brainstorm/design, grill or stress-test a plan, resolve design-blocking terms
if echo "$PROMPT_LOWER" | grep -qE '\bbrainstorm\b|\bideate\b|\bdesign\s*(a|an|this|the|new)?\s*(\w+\s+)?(feature|component|system|api|flow|architecture)\b|\bexplore\s*(approach|option|idea|design|alternative)s?\b|\bthink\s*through\b|\bbefore\s*(i|we)?\s*(implement|code|build|start)\b|\bplan\s*(out|this|the)?\s*(feature|design|approach)\b|\bplan\s*(review|grill)\b|\breview\s*(this|the|my)?\s*plan\b|\bsketch\s*out\b|\bfigure\s*out\s*(how|what|the)\b|\bdesign\s*session\b|\bwhat\s*should\s*(i|we)\s*(build|implement|create)\b|\bgrill\s*(me|this|the|my)?\b|stress[\s-]?test\s*(this|the|my)?\s*(plan|design|idea)|\bCONTEXT\.md\b|\bADR\b|domain\s*(language|glossary|term)'; then
	skills+="brainstorming-ideas "
fi

# using-modern-cli: Modern CLI tools for better performance
# Triggers: grep/find/cat alternatives, bash scripts, command optimization
if echo "$PROMPT_LOWER" | grep -qE '\bripgrep\b|\brg\b.*search|\bfd\b.*find|\bbat\b.*file|\bsd\b.*replace|\beza\b|\bdust\b|\bprocs\b|\bmodern\s*cli\b|better\s*than\s*(grep|find|cat|sed|ls)|replace.*(grep|find|cat|sed|ls)|faster.*(search|find)|\.gitignore.*respect|bash\s*script|command.*chain|optimize.*(command|cli|shell)'; then
	skills+="using-modern-cli "
fi

# improving-tests: Review, refactor, improve tests, and TDD workflow
# Triggers: improve tests, refactor tests, coverage, TDD, red-green-refactor
if echo "$PROMPT_LOWER" | grep -qE '\bimprove\s*(my|the|these)?\s*tests?\b|\brefactor\s*(my|the|these)?\s*tests?\b|\btest\s*coverage\b|\bcombine\s*(the|my)?\s*tests?\b|\btable[\s-]?driven\b|\bparametri[sz]e\b|\btest\.each\b|\beliminate\s*test\s*waste\b|\btest\s*(quality|improvement|cleanup)\b|\btdd\b|test[\s-]?first|red[\s-]?green[\s-]?refactor|write\s*(the\s*)?test\s*first'; then
	skills+="improving-tests "
fi

# learning-patterns: Extract learnings and generate customizations/domain docs
# Triggers: learn, learnings, adapt config, session patterns, domain language capture
if echo "$PROMPT_LOWER" | grep -qE '\blearn\b.*\b(from|session|pattern|conversation)\b|\bextract\s*(the)?\s*learnings?\b|\bwhat\s*did\s*(we|i)\s*learn\b|\bsave\s*(the)?\s*learnings?\b|\badapt\s*(the|my)?\s*(config|configuration|settings)\b|\bsession\s*learnings?\b|\bimprove\s*claude\s*code\b|\bcustomiz.*(claude|config)\b|\b(learn|record)\s*from\s*(this|the|our)\s*(session|conversation|chat)\b|capture\s*(domain|term|language)|save\s*(domain|term|language)|record\s*(ADR|decision|out[\s-]?of[\s-]?scope)'; then
	skills+="learning-patterns "
fi

# spec:status: Progress overview for spec-driven projects
# Triggers: project status, progress, how far along, spec status
if echo "$PROMPT_LOWER" | grep -qE '\b(project|spec|task)\s*(status|progress|overview)\b|\bhow\s*(far|much|many|is)\s*(along|done|progress|left|remain|complete)\b|\bwhat.*(done|left|remain|progress|status)\b|\bshow\s*(me\s*)?(progress|status|overview)\b|\bhow.*project\s*(going|doing)\b'; then
	skills+="spec:status "
fi

# spec:help: Quick methodology guide for spec-driven development
# Triggers: how does spec work, spec guide, spec methodology
if echo "$PROMPT_LOWER" | grep -qE '\bhow\s*does\s*spec\b|\bspec\s*(guide|help|methodology|workflow|reference)\b|\bspec[\s-]driven\s*(guide|help|how)\b|\bwhat\s*(are|is)\s*(the)?\s*spec\s*(command|workflow|phase)'; then
	skills+="spec:help "
fi

# spec:interview: Requirement extraction with domain/out-of-scope context
# Triggers: gather requirements, PRD, interview, out-of-scope triage
if echo "$PROMPT_LOWER" | grep -qE '\b(requirements?|prd|product\s*requirements?)\b|spec\s*interview|interview\s*(me|for|about)|out[\s-]?of[\s-]?scope|triage\s*(issue|request|feature)'; then
	skills+="spec:interview "
fi

# spec:plan: Create vertical-slice task plan
# Triggers: implementation plan, break into tasks/issues, vertical slices
if echo "$PROMPT_LOWER" | grep -qE 'spec\s*plan|implementation\s*plan|break\s*(this|it)?\s*(into)?\s*(tasks|issues|tickets)|vertical\s*slice|tracer\s*bullet|create\s*(tasks|issues)'; then
	# Plan review/grilling belongs to brainstorming-ideas, not task generation.
	if ! echo "$PROMPT_LOWER" | grep -qE '\b(grill|stress[\s-]?test|challenge|review)\b.*\bplan\b|\bplan\b.*\b(grill|stress[\s-]?test|challenge|review)\b'; then
		skills+="spec:plan "
	fi
fi

# spec:work: Main workflow - select, plan, implement, verify
# Triggers: start/continue spec work, next task
if echo "$PROMPT_LOWER" | grep -qE '\b(start|begin|continue|resume)\s*(spec\s*)?(work|task|implementation)\b|\bnext\s*(ready\s*)?(task|work)\b|\bwork\s*on\s*(the\s*)?(next|a)\s*task\b|\bspec[\s:]work\b|\bpick\s*up\s*(a\s*)?(new\s*)?task\b'; then
	skills+="spec:work "
fi

# analyzing-usage: Analyze Claude Code usage, cost, and efficiency
# Triggers: usage, cost, spending, tokens, burn rate, budget
if echo "$PROMPT_LOWER" | grep -qE '\busage\b.*\b(report|analyz|stat|cost|token|session)\b|\bcost\b.*\b(analyz|report|break|track|session)\b|\bspending\b|\bburn\s*rate\b|\btoken\s*(usage|count|stat)\b|\banalyze\s*(my|the)?\s*usage\b|\bhow\s*much\s*(did|have|am)\s*(i|we)\s*(spend|spent|using)\b|\bbudget\b.*\b(check|track|monitor)\b|\befficiency\b.*\b(report|analyz)\b|\bccusage\b'; then
	skills+="analyzing-usage "
fi

# debating-ideas: Dialectic agents stress-test design decisions
# Triggers: debate, argue both sides, devil's advocate, stress test idea
if echo "$PROMPT_LOWER" | grep -qE '\bdebate\b|\bargue\s*(both)?\s*sides\b|\bdevil.?s?\s*advocate\b|\bstress[\s-]?test\s*(this|the|my|an?)?\s*(idea|approach|design|decision|claim)\b|\bpros\s*(and|&)\s*cons\s*(of)?\s*(this|the|my)?\s*(approach|design|decision)\b|\bchallenge\s*(this|the|my)?\s*(idea|approach|assumption)\b|\brigorous\s*(evaluat|review|analys)\b|\bdialectic\b'; then
	skills+="debating-ideas "
fi

# evolving-config: Audit Claude Code config against latest features
# Triggers: evolve, self-improve, audit config, what's new in claude code
if echo "$PROMPT_LOWER" | grep -qE '\bevolve\b|\bself[\s-]?improv\b|\baudit\s*(my|the)?\s*(config|configuration|settings|setup)\b|\bwhat.?s\s*new\s*in\s*claude\s*code\b|\bupgrade\s*(my|the)?\s*(config|configuration|settings)\b|\bcheck\s*(for)?\s*(improvement|update)s?\b|\bare\s*(we|my\s*settings?)\s*up[\s-]?to[\s-]?date\b|\blatest\s*(claude|features)\b|\bimprove\s*(my|the)?\s*(claude|config|setup)\b'; then
	skills+="evolving-config "
fi

# reviewing-cc-config: Review Claude Code configuration for context efficiency
# Triggers: review config, config review, context review, review cc config, review my setup, review skills/agents/hooks
if echo "$PROMPT_LOWER" | grep -qE '\breview\s*(my|the|cc|claude)?\s*(config|configuration|setup)\b|\b(config|configuration|setup)\s*review\b|\bcontext\s*review\b|\breview\s*(my|the)?\s*(skills|agents|hooks)\b|\bconfig(uration)?\s*(quality|health|check)\b'; then
	skills+="reviewing-cc-config "
fi

# using-gemini: Consult Gemini CLI for second opinions or web search
# Triggers: ask gemini, gemini search, gemini opinion, second AI perspective
if echo "$PROMPT_LOWER" | grep -qE '\bask\s*gemini\b|\bgemini\s*(search|opinion|review|check|consult)\b|\bget\s*gemini\b|\bconsult\s*gemini\b|\bgemini\s*-p\b|\bsecond\s*(ai|opinion|perspective)\b'; then
	skills+="using-gemini "
fi

# smart-explore: AST-based code navigation via claude-mem
# Triggers: code structure, file outline, structural exploration
if echo "$PROMPT_LOWER" | grep -qE '\b(code|file)\s*structure\b|\boutline\b.*\b(file|code|class|module)\b|\bstructural\s*(view|map|overview)\b|\bwhat.?s\s*in\s*this\s*file\b|\bexplore\s*(the\s*)?(code|codebase)\s*(structure)?\b|\bshow\s*(me\s*)?(the\s*)?(file|code)\s*structure\b|\bast\s*(pars|view|explor)\b|\bsmart[\s_-]?explore\b'; then
	skills+="smart-explore "
fi

# linting-instructions: Lint plugin prompts against Anthropic model cards
# Triggers: only when working on skills/agents/plugins — lint prompts, audit instructions, model card review
if echo "$PROMPT_LOWER" | grep -qE '\blint\s*(the|my|all)?\s*(skill|agent|plugin)?\s*instructions?\b|\breview\s*(the|my|all)?\s*(skill|agent|plugin)\s*(prompts?|instructions?)\b|\baudit\s*(the|my)?\s*(skill|agent|plugin)\s*(prompts?|instructions?)\b|\binstruction\s*quality\b|\bprompt\s*quality\b|\bmodel\s*card\s*(lint|review|check|rules?)\b|\bsystem\s*card\s*(lint|review|check|rules?)\b'; then
	skills+="linting-instructions "
fi

# ccgram-messaging: Inter-agent messaging via ccgram swarm
# Triggers: ccgram commands, peer messaging, inbox, broadcast, swarm collaboration, agent-to-agent
if echo "$PROMPT_LOWER" | grep -qE '\bccgram\b|\binbox\b.*\b(message|agent|peer)\b|\bmessage\s*(other|another|peer|agent|window)\b|\bbroadcast\b.*\b(agent|peer|team|status)\b|\bswarm\b|\blist[\s-]?peers\b|\bpeer\s*(message|discovery|status)\b|\binter[\s-]?agent\b|\bagent[\s-]?to[\s-]?agent\b|\bsend\s*(a\s*)?(message|msg)\s*(to)?\s*(agent|peer|window|@)\b|\bask\s*(another|other|the)\s*agent\b|\breply\s*(to)?\s*(the)?\s*(message|msg|agent)\b|\bspawn\s*(a\s*)?(new\s*)?(agent|window)\b|\bagent\s*(collaborat|communicat|coordinat)\b|\btmux\s*messag\b|\bcheck\s*(my|the)?\s*inbox\b'; then
	skills+="ccgram-messaging "
fi

# exploring-repos: Explore public GitHub repos via DeepWiki
# Triggers: repo architecture, how does repo work, deepwiki, explore repo, codebase patterns
if echo "$PROMPT_LOWER" | grep -qE '\bdeepwiki\b|\bexplore\s*(the\s*)?(repo|repository|codebase|project)\b|\brepo\s*(architecture|structure|design|patterns?)\b|\bhow\s*does\s*\S+/\S+\s*work\b|\bunderstand\s*(the\s*)?(repo|repository|codebase|project)\b|\bcodebase\s*(overview|architecture|structure|understanding)\b|\bwiki\s*(for|of|about)\s*(the\s*)?(repo|repository)\b|\bexplore\s*\S+/\S+\b|\bdesign\s*patterns?\s*(in|of|used\s*by)\b|\bhow\s*(is|are)\s*\S+\s*(structured|organized|designed|architected)\b'; then
	skills+="exploring-repos "
fi

# mem-history: Query project history via claude-mem
# Triggers: past sessions, previous decisions, project timeline, memory search
if echo "$PROMPT_LOWER" | grep -qE '\blast\s*session\b|\bdid\s*we\s*already\b|\bprevious\s*session\b|\bremember\s*when\b|\bwhat\s*did\s*we\s*decide\b|\bpast\s*(issue|bug|decision|fix)\b|\brecurring\s*bug\b|\bproject\s*(history|timeline)\b|\btimeline\b.*\b(project|feature|change)\b|\bwhat\s*happened\s*with\b|\bmem[\s-]?history\b|\bmem[\s-]?search\b|\bclaude[\s-]?mem\b'; then
	skills+="mem-history "
fi

# coding: Implementation process discipline — assumptions and verifiable goals
# Triggers: implement, write/create/build/add code constructs in any language
# Co-fires alongside language-specific skills (writing-go, writing-python, etc.)
if echo "$PROMPT_LOWER" | grep -qE '\bimplement\b|\bwrite\s+(a\s+)?(function|method|class|module|script|service|handler|middleware|endpoint|api|component|struct|interface|type|trait|enum)\b|\bcreate\s+(a\s+)?(function|method|class|module|script|service|handler|endpoint|component|struct)\b|\badd\s+(a\s+)?(feature|function|method|endpoint|handler|route|command|flag|option|field|property)\b|\bbuild\s+(a\s+)?(feature|module|service|api|system|component|pipeline|cli|tool)\b|\bdevelop\s+(a\s+)?(feature|module|service|component|api)\b|\bcode\s+(this|up|a|the)\b'; then
	# Exclude review/fix/commit/doc tasks — those have dedicated skills
	if ! echo "$PROMPT_LOWER" | grep -qE '\breview\b|\bfix\b|\bcommit\b|\bdocument\b|\brefactor\b'; then
		skills+="coding "
	fi
fi

# Output only if skills detected (silent when no match)
if [[ -n "$skills" ]]; then
	skills="${skills% }"
	echo "→ Consider skills: $skills"
fi
# Silent exit when no skills detected - reduces context noise
