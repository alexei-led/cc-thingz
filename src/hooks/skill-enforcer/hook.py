#!/usr/bin/env python3
"""Suggest skills that match the prompt. Advisory: silent on no match, never blocks.

One process with precompiled patterns stays far below the hook timeout; the old
shell version forked ~38 grep/jq processes per prompt and timed out under load.
"""

import json
import os
import re
import sys

RELEASE = re.compile(
    r"\b(prepare|cut|create|finalize|tag|ship|publish"
    r"|release|bump)\b.{0,50}\b(software[\s]+)?(release"
    r"|v[0-9]+\.[0-9]+\.[0-9]+)\b|\b(write|draft|prepare"
    r"|review|repair|edit|rewrite|update|improve|revise"
    r"|fix)\b.{0,35}\b(release notes|release-note|changelog section)\b"
    r"|\b(release notes|release-note|changelog section)\b.{0,35}\b(write"
    r"|draft|prepare|review|repair|edit|rewrite|update"
    r"|improve|revise|fix)\b|(подготов|выпусти|выпустить"
    r"|опубликуй|опубликовать|создай|создать|тегируй"
    r"|подготовь).{0,55}(релиз|v[0-9]+\.[0-9]+\.[0-9]+)"
    r"|(напис|подготов|проверь|исправ|состав|отредактир"
    r"|обнов|перепиш).{0,45}(заметк.{0,10}(релиз)|release notes"
    r"|changelog)"
)
ARTICLE = re.compile(
    r"\b(publish|post)\b.{0,40}\b(article|blog post|newsletter"
    r"|news story|press release)\b"
)
FOLLOW_UP = re.compile(
    r"yes|no|ok|okay|sure|thanks|continue|proceed|go ahead|do it|looks good|lgtm"
)

# (skill, include, exclude). Output keeps this order; releasing-code comes first.
RULES = [
    (
        "writing-go",
        (
            r"\.go\b|go\.(mod|sum)|\bgo (test|build|run|fmt|vet"
            r"|mod|get|generate)|golangci|mockery|\bgolang\b"
            r"|\bgoroutines?\b|\bdefer\b.*func|urfave|testify"
            r"|cobra/|idiomatic go|in go\b|go (code|project|package"
            r"|module|interface|struct)|write.*\bgo\b|implement.*\bgo\b"
            r"|\berror\s*handling\b.*go"
        ),
        None,
    ),
    (
        "writing-rust",
        (
            r"\.rs\b|cargo\.(toml|lock)|\bcargo (test|build|run"
            r"|check|fmt|clippy|doc|bench|nextest)\b|rustfmt"
            r"|\bclippy\b|rust-analyzer|\brustc\b|\brustup\b"
            r"|\brust\b|\bcrate\b|borrow checker|\btraits?\b.*\bimpl\b"
            r"|\bimpl\b.*\btraits?\b|\bderive\b.*\bdebug\b|tokio"
            r"|serde|idiomatic rust|write.*rust|implement.*rust"
        ),
        None,
    ),
    (
        "writing-python",
        (
            r"\.pyi?\b|pyproject|requirements\.txt|setup\.py"
            r"|__init__|python[3]?\b|\buv (run|pip|sync|add|lock)"
            r"|\bruff\b|\bty\b|pytest|poetry\b|mypy\b|django"
            r"|flask|fastapi|pandas|numpy|pydantic|dataclass"
            r"|type\s*hint|\btyping\b|asyncio|pip install|write.*python"
            r"|implement.*python"
        ),
        None,
    ),
    (
        "writing-typescript",
        (
            r"\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)\b|typescript"
            r"|tsconfig|package\.json|\bnpm\b|\bbun\b|\byarn\b"
            r"|\bvite\b|react|next\.?js|node\.?js|\bexpress\b"
            r"|\best\b|vitest|jest|biome|oxlint|oxfmt|eslint"
            r"|prettier|write.*typescript|implement.*\bts\b|strict typing"
        ),
        None,
    ),
    (
        "writing-csharp",
        (
            r"\.cs\b|\.csproj\b|\.sln\b|\bdotnet\b|(^|[\W_])c#([\W_]"
            r"|$)|\bcsharp\b|(^|[\W_])\.net([\W_]|$)|\basp\.net\b"
            r"|\bmsbuild\b|\bnuget\b|\bxunit\b|\bnunit\b|\bmstest\b"
            r"|\bblazor\b|entity framework"
        ),
        None,
    ),
    (
        "writing-java-kotlin",
        (
            r"\.java\b|\.kt\b|\.kts\b|pom\.xml|build\.gradle(\.kts)?"
            r"|settings\.gradle(\.kts)?|\bgradle\b|\bmaven\b"
            r"|\bmvnw?\b|\bjunit\b|\bmockito\b|\bmockk\b|\bkotest\b"
            r"|\bktlint\b|\bdetekt\b|\bspotless\b|\bgoogle-java-format\b"
            r"|\bopenjdk\b|\bjdk\b|\bjvm\b|(^|[\W_])java([\W_]"
            r"|$)|\bkotlin\b|\bkotlinc\b|\bspring\s*boot\b|\bmicronaut\b"
            r"|\bquarkus\b|\bktor\b|\bjakarta\b|\bhibernate\b"
            r"|\bvirtual\s+threads?\b|\bsealed\s+(class|interface)s?\b"
            r"|\brecords?\b.*\bjava\b|\bsuspend\s+fun\b|\bcoroutines?\b"
        ),
        None,
    ),
    (
        "operating-infra",
        (
            r"\.tf\b|\.tfvars|dockerfile|docker-compose|chart\.yaml"
            r"|kustomization|values\.yaml|\bkubectl\b|\bhelm\b"
            r"|\bkustomize\b|\bterraform\b|\btofu\b|kubernetes"
            r"|k8s\b|\bpod[s]?\b|\bdeployment[s]?\b|\bingress\b"
            r"|\bconfigmap|\bnamespace[s]?\b|\bstatefulset|\bdaemonset"
            r"|cronjob|\bhpa\b|networkpolic|manifest|container.*(image"
            r"|registry|port)|service\s*account|node\s*pool|github.*action"
            r"|\.github/workflows|workflow.*yaml|\bgcloud\b|\bgsutil\b"
            r"|\bbq\s|\baws\s|bigquery|cloud\s*(run|function"
            r"|sql|storage)|gke\b|gcs\b|pubsub|dataflow|firestore"
            r"|spanner|\bs3\b|\bec2\b|aws.*lambda|lambda.*(function"
            r"|handler)|\becs\b|\beks\b|\brds\b|dynamodb|\bsqs\b"
            r"|\bsns\b|cloudformation|cloudwatch|iam.*(role|policy"
            r"|permission)|\bbucket[s]?\b|--project\b|--region\b"
            r"|systemctl|journalctl|\bnginx\b|\blinux\s*(host"
            r"|service|instance)|\bdeploy\s*check\b|\bcheck\s*(my"
            r"|the)?\s*deploy(ment)?\b|\bvalidate\s*(my|the)?\s*(deployment"
            r"|infrastructure|infra|k8s|kubernetes|helm|terraform"
            r"|config)s?\b|\bcheck\s*(my|the)?\s*(k8s|kubernetes"
            r"|helm|terraform|workflow|action)\s*(config|manifest"
            r"|file)s?\b|\bverify\s*(the)?\s*infrastructure\b"
            r"|\binfra\s*check\b|\bdeploy\s*to\s|apply\s*(the\s*)?(changes"
            r"|infra)|terraform\s*apply|helm\s*(upgrade|install)"
            r"|kubectl\s*apply|rollout"
        ),
        None,
    ),
    (
        "looking-up-docs",
        (
            r"\bctx7\b|\bcontext7\b|context7[\s-]cli|/[a-z0-9._-]+/[a-z0-9._-]+\s+(library"
            r"|docs|version)|\b(docs|documentation)\s+(for|of"
            r"|on|about|say|says)\b|api\s*(reference|docs)|look\s*up.*(docs"
            r"|api|syntax|usage|reference|examples)|find.*(docs"
            r"|documentation|reference)|check.*(docs|documentation)"
            r"|man\s*page|reference.*(guide|manual)|official.*(docs"
            r"|documentation)|library.*docs|version.*specific"
            r"|syntax\s*for|examples\s*of|how\s*to\s*use\s*\w+"
        ),
        (
            r"\bvs\b|\bcompare\b|\bbest\s*practice\b|\bpros\s*(and"
            r"|&)\s*cons\b|\bwhich.*(better|should)\b|\b(write"
            r"|rewrite|update|improve|restructure|reorganize"
            r"|edit|polish|revise|refresh|draft|clean[\s]*up"
            r"|make)\b.{0,40}\b(readme|docs|documentation|user[\s-]?guide"
            r"|architecture[\s]+doc(ument)?s?|front[\s-]?page"
            r"|changelog)\b|(обнови|перепиши|улучши|напиши|исправь"
            r"|сделай|переделай).{0,80}(документац|readme|ридми"
            r"|гайд|руководств)"
        ),
    ),
    (
        "researching-web",
        (
            r"\bresearch\b|search.*(web|online)|look\s*up.*online"
            r"|find\s*out.*(about|if|whether)|compare.*(tool"
            r"|lib|framework|approach|option|technolog)|(\w+)\s+vs\s+(\w+)"
            r"|pros\s*(and|&)\s*cons|trade[\s-]?off|which.*(tool"
            r"|lib(rary)?|framework|approach|option|technolog(y"
            r"|ies)|database|language|runtime|package|service).*(better"
            r"|should|recommend)|latest.*(version|release|update)"
            r"|current.*(version|best)|what.?s\s*new\s*in|best\s*practice"
            r"|up[\s-]?to[\s-]?date|\b20[0-9]{2}\b|industry\s*standard"
            r"|owasp|recommended\s*(practice|approach|pattern)"
            r"|perplexity"
        ),
        None,
    ),
    (
        "using-git-worktrees",
        (
            r"worktree|git\s*worktree|isolat.*(work|branch|develop"
            r"|implement|environment)|separate.*(workspace|environment"
            r"|branch)|parallel.*(branch|work|develop)|work.*(multiple"
            r"|parallel).*branch|fresh.*(workspace|environment"
            r"|branch)|feature.*isolation"
        ),
        None,
    ),
    (
        "cleanup-git",
        (
            r"cleanup.*(git|branch|worktree)|clean\s+up.*(git"
            r"|branch|worktree)|prune.*(branch|worktree|git)"
            r"|tidy.*git|remove.*merged.*branch|delete.*merged.*branch"
            r"|gone\s+branches|stale\s+worktrees"
        ),
        None,
    ),
    (
        "configuring-git-hygiene",
        (
            r"git[\s-]?(hygiene|guardrails)|pre[\s-]?commit|pre[\s-]?push"
            r"|gitleaks|git[\s-]?leaks|secret\s+scan.*git|git\s+hooks?"
            r"|core\.hooksPath|hooksPath|\.gitignore|gitignore"
            r"|git\s+config.*(best|setup|hygiene|sign|pull|prune"
            r"|includeif)"
        ),
        None,
    ),
    (
        "reviewing-code",
        (
            r"\breview\b.*\b(code|changes|this|my|the)\b|\bcode\s*review\b"
            r"|\bcheck\s*(this|my|the)?\s*code\b|\bdeep\s*(code\s*)?review\b"
            r"|\bfeedback\s*(on)?\s*(my|the|this)?\s*code\b|review\s*(my"
            r"|the|these)?\s*(changes|implementation|pr)\b|critique\s*(my"
            r"|the|this)?\s*code|find\s*line[\s-]?level\s*refactoring\s*opportunities"
        ),
        (
            r"\b(config|configuration|setup|skills?|agents?|hooks?"
            r"|claude\.?md)\b"
        ),
    ),
    (
        "committing-code",
        (
            r"\bcommit\b|\bsave\s*(my|the)?\s*changes\b|\bcreate\s*(a\s*)?commit\b"
            r"|\bbundle\s*commits?\b|\bgit\s*commit\b|\bcommit\s*(my"
            r"|the|these)?\s*(changes|work|code)\b|\bsave\s*(my)?\s*work\b"
        ),
        None,
    ),
    (
        "fixing-code",
        (
            r"\bfix\s*(all|the|my|these|this|any)?\s*(issue|error"
            r"|bug|problem|warning|lint|test|failure|type\s*error"
            r"|build|compilation)s?\b|\bfix\s*(it|this|them|everything)\b"
            r"|\bresolve\s*(the|all|these)?\s*(issue|error|bug)s?\b"
            r"|\baddress\s*(the|all)?\s*(issue|error|warning)s?\b"
            r"|make\s*(it|the|tests?|build)\s*(pass|work|green)\b"
            r"|\bdebug\b|\bdiagnos(e|is)\b|\brepro(duce)?\b|\bperformance\s*regression\b"
            r"|\bthrow(s|ing)?\b|\bcrash(es|ing)?\b|\bbroken\b"
        ),
        None,
    ),
    (
        "documenting-code",
        (
            r"\b(write|rewrite|update|improve|restructure|reorganize"
            r"|edit|polish|revise|refresh|draft|clean[\s]*up"
            r"|make)\b.{0,40}\b(readme|docs|documentation|user[\s-]?guide"
            r"|architecture[\s]+doc(ument)?s?|front[\s-]?page"
            r"|changelog)\b|(обнови|перепиши|улучши|напиши|исправь"
            r"|сделай|переделай).{0,80}(документац|readme|ридми"
            r"|гайд|руководств)|\bdocument\s+(this|the|my|these)\s+(code"
            r"|changes|function|api|module)\b|\badd\s*(some|more)?\s*documentation\b"
            r"|\bdocstrings?\b|\bjsdoc\b|\bgodoc\b"
        ),
        None,
    ),
    (
        "browser-automation",
        (
            r"\be2e\b.*\btest|\bplaywright\b|\bbrowser\s*(test"
            r"|testing|automation|check|validation|verify|verification"
            r"|exploration|inspect|debug|screenshot|record)\b"
            r"|\b(use|open|drive|inspect|explore|validate|verify"
            r"|record|screenshot|capture)\s*(a\s*)?(real\s*)?browser\b"
            r"|\bscreenshot\b|\bui\s*(test|testing|automation"
            r"|check|validation|verification|debug)\b|\brendered\s*(dom"
            r"|page|state|ui)\b|\bend[\s-]?to[\s-]?end\b|\bvisual\s*(test"
            r"|testing|check|regression|diff)\b|\baccessibility\s*(test"
            r"|testing|check|audit)\b|\ba11y\s*(test|check|audit)\b"
        ),
        None,
    ),
    (
        "writing-web",
        (
            r"\bhtml\s*(template|file|page|component)?\b|\bcss\s*(style"
            r"|file|class)?\b|\bstylesheet\b|\bhtmx\b|\bweb\s*(template"
            r"|page|component|form)\b|\bhtml\s*and\s*css\b|\bvanilla\s*js\b"
            r"|\bdom\s*manipulat|\.html\b|\.css\b"
        ),
        (
            r"\breact\b|\bvue\b|\bangular\b|\bnext\.?js\b|\bnode\.?js\b"
            r"|\btsx\b"
        ),
    ),
    (
        "brainstorming-ideas",
        (
            r"\bbrainstorm\b|\bideate\b|\bdesign\s*(a|an|this"
            r"|the|new)?\s*(\w+\s+)?(feature|component|system"
            r"|api|flow|architecture)\b|\bexplore\s*(approach"
            r"|option|idea|design|alternative)s?\b|\bthink\s*through\b"
            r"|\bbefore\s*(i|we)?\s*(implement|code|build|start)\b"
            r"|\bplan\s*(out|this|the)?\s*(feature|design|approach)\b"
            r"|\bsketch\s*out\b|\bfigure\s*out\s*(how|what|the)\b"
            r"|\bdesign\s*session\b|\bwhat\s*should\s*(i|we)\s*(build"
            r"|implement|create)\b|\bcontext\.md\b|\badr\b|domain\s*(language"
            r"|glossary|term)|\bgrill\s*(me|this|the|my)\b|\bdebate\b"
            r"|\bargue\s*(both)?\s*sides\b|\bdevil.?s?\s*advocate\b"
            r"|\bpros\s*(and|&)\s*cons\b|\bstress[\s-]?test\s*(this"
            r"|the|my|an?)?\s*(plan|design|idea|approach|decision"
            r"|claim)\b|\bchallenge\s+me\b|\bchallenge\s*(this"
            r"|the|my)?\s*(plan|design|idea|approach|assumption)\b"
            r"|\binterview\s*me\b.*\b(plan|design|approach)\b"
        ),
        None,
    ),
    (
        "writing-shell",
        (
            r"\.(sh|bash|zsh|fish|bats)\b|\b(shell|bash|zsh|fish)\s*(script"
            r"|function|pipeline|hook|config)\b|shebang|pipefail"
            r"|shellcheck|shfmt|checkbashisms|bats(-core|-assert)?"
            r"|shellspec|bashate|shellharden|shellcheck-sarif"
            r"|semgrep.*shell|\b(posix|portable)\s*sh\b|\b(command"
            r"|cli)\s*(pipeline|chain|runner|glue)\b|scriptable.*cli"
            r"|pipe.?friendly|better\s*than\s*(grep|find|cat"
            r"|sed|ls|du|ps|diff|curl|time|df|awk|cut)|replace.*(grep"
            r"|find|cat|sed|ls|du|ps|diff|curl|time|df|awk|cut)"
        ),
        None,
    ),
    (
        "improving-tests",
        (
            r"\bimprove\s*(my|the|these)?\s*tests?\b|\brefactor\s*(my"
            r"|the|these)?\s*tests?\b|\btest\s*coverage\b|\bcombine\s*(the"
            r"|my)?\s*tests?\b|\btable[\s-]?driven\b|\bparametri[sz]e\b"
            r"|\btest\.each\b|\beliminate\s*test\s*waste\b|\btest\s*(quality"
            r"|improvement|cleanup)\b|\btdd\b|test[\s-]?first"
            r"|red[\s-]?green[\s-]?refactor|write\s*(the\s*)?test\s*first"
        ),
        None,
    ),
    (
        "spec-flow",
        (
            r"\bspec[\s-]?flow\b|\bspec[\s-]?(status|progress"
            r"|overview|guide|help|methodology|workflow|reference"
            r"|init|new|plan|work|done)\b|\bspec[\s-]driven\b"
            r"|\b(task|project)\s*(status|progress|overview)\b"
            r"|\bhow\s*(does|to)\s*spec\b|\bnext\s*(ready\s*)?(task"
            r"|work)\b|\bwork\s*on\s*(the\s*)?(next|a)\s*task\b"
            r"|\b(start|begin|continue|resume)\s*(spec\s*)?(work"
            r"|task|implementation)\b|\b(mark|close|finish|complete)\s*(a\s*)?(spec\s*)?(t"
            r"ask|ticket)\b|\bcheckpoint\s*(task|work|session)\b"
            r"|\bvertical\s*slice\b|\btracer\s*bullet\b|\bbreak\s*(this"
            r"|it)?\s*(into)?\s*(tasks|issues|tickets)"
        ),
        (
            r"\b(grill|stress[\s-]?test|challenge|review)\b.*\bplan\b"
            r"|\bplan\b.*\b(grill|stress[\s-]?test|challenge"
            r"|review)\b"
        ),
    ),
    (
        "evolving-config",
        (
            r"\bevolve\b|\bself[\s-]?improv\b|\baudit\s*(my|the)?\s*(config"
            r"|configuration|settings|setup)\b|\bwhat.?s\s*new\s*in\s*claude\s*code\b"
            r"|\bupgrade\s*(my|the)?\s*(config|configuration"
            r"|settings)\b|\bcheck\s*(for)?\s*(improvement|update)s?\b"
            r"|\bare\s*(we|my\s*settings?)\s*up[\s-]?to[\s-]?date\b"
            r"|\blatest\s*(claude|features)\b|\bimprove\s*(my"
            r"|the)?\s*(claude|config|setup)\b"
        ),
        None,
    ),
    (
        "reviewing-instructions",
        (
            r"\b(lint|audit|review|score|check)\s+(the\s+|my\s+"
            r"|this\s+|all\s+|a\s+)?(skill|agent|plugin|instruction"
            r"|prompt)s?\b|\b(reviewing|auditing|scoring)[- ]instructions\b"
            r"|\b(skill|agent|instruction|prompt)\s*(quality"
            r"|score|audit|review|lint)\b|\breview\s+\S*(skill\.md"
            r"|agents?\.md|claude\.md)\b|\bsignal\s+density\b"
            r"|\bfluff\s+(meter|score)\b|\bprompt\s*(quality"
            r"|lint|audit|review|score)\b|\binstruction\s*(quality"
            r"|lint|audit|review|score)\b|\bmodel\s*card\s*(lint"
            r"|review|check|rules?)\b"
        ),
        None,
    ),
]
COMPILED = [
    (skill, re.compile(inc, re.M), exc and re.compile(exc, re.M))
    for skill, inc, exc in RULES
]


def suggest(prompt: str) -> list[str]:
    text = prompt.lower()
    if len(text) < 10 or "skill(" in text or FOLLOW_UP.fullmatch(text):
        return []
    release = bool(RELEASE.search(text)) and not ARTICLE.search(text)
    skills = ["releasing-code"] if release else []
    for skill, include, exclude in COMPILED:
        if skill == "documenting-code" and release:
            continue
        if include.search(text) and not (exclude and exclude.search(text)):
            skills.append(skill)
    return skills


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    pi = payload.get("event") == "prompt-submit" and isinstance(
        payload.get("piEvent"), dict
    )
    if pi:
        event = payload["piEvent"]
        prompt = event.get("prompt") or event.get("text") or event.get("input") or ""
    else:
        prompt = payload.get("prompt") or ""
    enabled = os.environ.get("HOOK_SKILL_ENFORCER", "1") != "0"
    skills = suggest(prompt) if enabled and isinstance(prompt, str) else []
    if skills:
        # Pi requires stdout to hold only the decision, so hints go to stderr there.
        hint = "→ Consider skills: " + " ".join(dict.fromkeys(skills))
        print(hint, file=sys.stderr if pi else sys.stdout)
    if pi:
        print('{"decision":"allow"}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
