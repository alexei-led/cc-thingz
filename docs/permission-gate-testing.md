# Permission gate design and verification

## Policy

This is a developer warning aid, not an approval sandbox. Default behavior is
blacklist-only: normal and unknown commands pass. A positively recognized local
dangerous invocation or explicit user deny can block. Allow rules waive warnings
for exact literal invocations; they never make unrelated commands forbidden.

The gate does not classify every interpreter, remote program, or dynamically
constructed executable. Those programs can perform destructive actions without
a warning. OS permissions and isolation are the enforcement boundary.

## Research and decisions

- [Claude Code permissions](https://code.claude.com/docs/en/permissions#bash-permission-rules)
  describe command/operator-aware checks, deny precedence, and the limits of
  invocation-shaped rules. Preserve deny precedence and inspect command
  structure rather than searching all argument text as executable code.
- [Codex rules](https://developers.openai.com/codex/rules) distinguish literal
  argument matching from scripts that require shell interpretation. Keep
  warning exceptions on the strict literal parser. Unlike Codex's sandbox
  approval policy, this warning gate intentionally does not prompt for all
  unknown syntax.
- [Bash redirections](https://www.gnu.org/software/bash/manual/html_node/Redirections.html)
  specify that quoting any part of a heredoc delimiter suppresses body expansion.
  Unquoted heredocs and here-strings can perform local substitutions. Inspect
  those substitutions, not the body text as shell commands.
- [Bash command expansion](https://www.gnu.org/software/bash/manual/html_node/Simple-Command-Expansion.html)
  separates redirections and assignments from the executable and arguments.
  Keep redirection metadata while scanning; do not confuse a quoted `>`
  argument with an actual redirection.

The scanner deliberately recognizes a limited set of shell structures and
common runner argument conventions. It never executes expansions or infers
that a command is safe from a raw-string wildcard. Unsupported structures are
not an automatic denial. No shell-parser dependency or general policy language
is required for these warning semantics.

## Tests

Run the focused contract and real-session tests:

```bash
bun test tests/pi-extensions/compatibility/permission-gate.test.ts \
  tests/pi-extensions/compatibility/permission-rules.test.ts \
  tests/pi-extensions/compatibility/permission-gate.session.test.ts --isolate
```

The contracts cover:

- The reported `sed`, `rg`, `head`, `cut`, `ls`, pipeline, redirection,
  glob, and command-chain forms, with no policy, user grants, trusted project
  grants, and unrelated user denies.
- Quoted source, literal warning words, heredocs, here-strings, parameter
  expansions, command substitutions, runner options, and adjacent redirections.
- Direct dangerous controls, flags after operands, explicit denies in compound
  commands, trust, headless eligibility, UI refusal/approval, hook vetoes, and
  validation of hook-supplied replacements.

The real-session fixture uses Pi's actual `AgentSession`, extension dispatcher,
hook runner, Bash backend, and nested `executeTool` path. Only the model stream,
network boundary, and UI adapter are test doubles. No model API or VM is used.

Benign commands run against temporary files. Potentially destructive program
names resolve to harmless fixture executables that record execution. A denied
case must have a gate/hook denial reason and must leave the execution marker
unchanged; an OS error alone is not a passing denial test. Positive exceptions
and explicit UI approval must execute the fixture program.

## Limits

These tests do not prove arbitrary Bash interpretation, executable identity,
cloud destination identity, or OS isolation. The UI adapter is tested, not a
live terminal dialog. User shell startup, command prefixes, executable lookup,
and later extensions remain trusted. Real-session execution tests require the
project's POSIX/Bash test environment; they do not establish Windows behavior.
