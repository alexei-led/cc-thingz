---
name: reviewing-code
description: Sequential code review for security, quality, tests, and architecture. Use when reviewing code, checking changes, reviewing PRs, or looking for deep-module/refactoring opportunities.
---

# Code Review

Review the current diff or specified scope for security, quality, test coverage, and architecture issues. Ground every claim in code or tool output.

## Step 1: Determine scope

Read the diff:

```bash
git diff --name-only HEAD
git diff HEAD
```

If the user supplied paths or a branch, use those instead.

## Step 2: Detect languages and domain docs

Categorize changed files:

- `.go` — Go
- `.py` — Python
- `.ts`, `.tsx` — TypeScript
- `.html`, `.css`, `.js` — Web

If present, read relevant `CONTEXT.md`, `CONTEXT-MAP.md`, and `docs/adr/` files before naming architectural findings.

## Step 3: Run linters and checks

Use real tool calls before conclusions.

```bash
# Go
golangci-lint run ./... 2>&1 | head -100
go vet ./...
go test -race ./... 2>&1 | head -100

# Python
ruff check . 2>&1 | head -100
mypy . 2>&1 | head -100
pytest --tb=short 2>&1 | head -100

# TypeScript
bun lint 2>&1 | head -100
bun tsc --noEmit 2>&1 | head -100
bun test 2>&1 | head -100
```

## Step 4: Review security

Check for hardcoded secrets, injection risks, unsafe deserialization, missing auth, IDOR, XSS, command execution, goroutine leaks, unchecked errors, and insecure browser patterns.

## Step 5: Review quality and tests

Check for:

- missing error handling
- duplicated logic
- dead code or commented-out blocks
- unclear names
- tests coupled to implementation
- missing happy/error/edge path tests

## Step 6: Review architecture when relevant

Use these terms exactly:

- **Module** — anything with an interface and implementation.
- **Interface** — everything callers must know: types, invariants, ordering, error modes, config, performance.
- **Seam** — where an interface lives.
- **Adapter** — concrete thing satisfying an interface at a seam.
- **Depth** — lots of behavior behind a small interface.
- **Leverage** — caller value from depth.
- **Locality** — change and verification concentrated in one place.

Apply the deletion test: if deleting a module makes complexity vanish, it was a pass-through. If complexity reappears across callers, it earned its keep.

Seam rule: one adapter means a hypothetical seam; two adapters means a real seam. Do not propose ports for decoration.

Find shallow modules, poor seams, fake ports, hidden coupling, and untestable interfaces. Propose deepening opportunities and explain how tests improve.

## Step 7: Report findings

Use this exact format. One line per finding. No preamble. No hedging.

```markdown
## Code Review

**Scope:** <description>
**Languages:** <list>

### CRITICAL
- `file:line` — <issue>. Fix: <action>.

### IMPORTANT
- `file:line` — <issue>. Fix: <action>.

### SUGGESTIONS
- `file:line` — <issue>. Fix: <action>.

### Architecture Opportunities
| Candidate | Files | Problem | Deepening Move | Test Benefit |
|-----------|-------|---------|----------------|--------------|
| ...       | ...   | ...     | ...            | ...          |

### Test gaps
- `func/method` in `file` — no test for <scenario>.

**Summary:** X critical, Y important, Z suggestions, W test gaps.
```

Omit empty sections. If no issues are found, say exactly what checks ran and why no findings survived review.
