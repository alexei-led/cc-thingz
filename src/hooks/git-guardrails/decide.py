#!/usr/bin/env python3
"""git-guardrails decision engine.

hook.sh forks this once, only for commands that contain a "git" word, and
translates its verdict into the hook's exit code / Pi JSON contract. This
process does the actual analysis: it tokenizes the command with shlex and
evaluates each git invocation's argv directly against a destructive-op
table, and verifies merge status for the "clean up merged work" exception
by shelling out to `git` (never another python3 process). A git
invocation is found by scanning every token position within a statement,
not only recognized command-start positions, so an unrecognized wrapper
(nice, timeout N, strace, ...) can never hide it from evaluation; `eval`
and `bash|sh|zsh|dash -c` are unwrapped one level so a *quoted* nested
command is tokenized too, while an ordinary quoted argument (a commit
message, a heredoc body) is not.

This is a mistake guard, not a shell sandbox: shlex tokenizes text, it does
not expand variables, globs, or git aliases, and heredoc bodies are stripped
rather than interpreted. A git call that opens a `$(...)`, backtick, or
`<(...)` substitution is still found; git hidden in a variable or alias is
not. A command this script cannot confidently parse is blocked (fail
closed) rather than silently allowed.

Command-name comparisons (`git`, and the `bash|sh|zsh|dash` interpreter set
for `-c` unwrapping) are case-insensitive: on macOS's default
case-insensitive filesystem, `GIT reset --hard` and `BASH -c 'GIT ...'`
resolve to and run the real binaries. Subcommands and flags (`RESET`,
`--Force`) are not: git's own argument parser resolves those from a fixed
table, not the filesystem, so case there is not a bypass.

Limit: `cd`/`pushd`/`popd` tracking understands a plain `cd <literal-path>`
only; anything else (bare `cd`, `cd -`, `pushd`, `popd`, a variable)
permanently loses directory trust for the rest of the command, so any later
merge-verified cleanup in it blocks. Upgrade trigger: a reported false
positive from one of those forms.

Input: environment variables set by hook.sh (GG_COMMAND, GG_CWD,
GG_ALLOW_FORCE_PUSH, GG_PATTERNS). Output: stdout is always exactly one of

    ALLOW
    BLOCK\n<rule description>\n<0 or 1: show the cleanup-allowed hint>

Exit code is always 0 once a decision is printed; a non-zero exit or empty
stdout means an unhandled bug, which hook.sh also treats as fail-closed
BLOCK.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys

SEPARATORS = {";", "&&", "||", "|", "&", "\n"}

# Known wrapper/keyword tokens that may precede `cd`/`pushd`/`popd` within
# one statement. Git itself is found by scanning every token position (see
# walk()), so this set no longer gates git detection - only cwd tracking,
# where an unrecognized wrapper is merely conservative, never unsafe.
STRIP_PREFIXES = {
    "do",
    "then",
    "else",
    "elif",
    "if",
    "while",
    "until",
    "!",
    "time",
    "sudo",
    "env",
    "xargs",
    "command",
    "{",
    "(",
}
VAR_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELL_DASH_C = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$")
INTERPRETERS = {"bash", "sh", "zsh", "dash"}

GLOBAL_VALUE_OPTS = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--config-env",
    "--super-prefix",
}
GLOBAL_FLAGS = {
    "--no-pager",
    "--paginate",
    "-P",
    "-p",
    "--bare",
    "--no-replace-objects",
    "--literal-pathspecs",
    "--glob-pathspecs",
    "--noglob-pathspecs",
    "--icase-pathspecs",
    "--no-optional-locks",
}
CLEANUP_SUBCOMMANDS = {"branch", "worktree"}


class ParseError(Exception):
    """The command could not be safely tokenized; the caller fails closed."""


def strip_heredocs(text: str) -> str:
    """Blanks heredoc bodies so quoted git-sounding text inside is never
    tokenized as a real command. Keeps the opening `<<[-~]WORD` line."""
    start_re = re.compile(r"<<([-~]?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
    out: list[str] = []
    i = 0
    while True:
        match = start_re.search(text, i)
        if not match:
            out.append(text[i:])
            break
        out.append(text[i : match.end()])
        dash_or_tilde, word = match.group(1), match.group(3)
        line_end = text.find("\n", match.end())
        if line_end == -1:
            # No newline after the opener: nothing left to safely tokenize.
            break
        body_start = line_end + 1
        indent = r"[ \t]*" if dash_or_tilde else ""
        terminator = re.compile(rf"^{indent}{re.escape(word)}[ \t]*$", re.MULTILINE)
        term_match = terminator.search(text, body_start)
        if not term_match:
            # Unterminated heredoc: drop the rest rather than tokenize a
            # body that was never meant to run as commands.
            break
        out.append("\n")
        i = term_match.end()
    return "".join(out)


def tokenize(text: str) -> list[str]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|\n")
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    try:
        return list(lexer)
    except ValueError as exc:
        raise ParseError(str(exc)) from exc


def split_statements(tokens: list[str]) -> list[list[str]]:
    spans: list[list[str]] = []
    start = 0
    for i, token in enumerate(tokens):
        if token in SEPARATORS:
            if i > start:
                spans.append(tokens[start:i])
            start = i + 1
    if start < len(tokens):
        spans.append(tokens[start:])
    return spans


class Ctx:
    """Tracks the working directory `cd` would leave a statement in, and
    whether that directory can still be trusted for merge verification."""

    def __init__(self, cwd: str, trusted: bool) -> None:
        self.cwd = cwd
        self.trusted = trusted

    def copy(self) -> Ctx:
        return Ctx(self.cwd, self.trusted)


def handle_cd(base: str, rest: list[str], ctx: Ctx) -> None:
    if base in ("pushd", "popd"):
        ctx.trusted = False
        return
    args = rest[1:]
    if len(args) != 1 or args[0].startswith("-"):
        ctx.trusted = False
        return
    target = args[0]
    ctx.cwd = target if os.path.isabs(target) else os.path.join(ctx.cwd, target)


def shell_dash_c_script(span: list[str], j: int) -> str | None:
    """True when span[j] is bash|sh|zsh|dash, span[j+1] is a -c-family
    flag, and its script is the last token of the statement - regardless
    of what precedes span[j] in the same statement (`nice bash -c '...'`
    unwraps exactly like a bare `bash -c '...'`)."""
    if j + 2 != len(span) - 1:
        return None
    return span[j + 2] if SHELL_DASH_C.match(span[j + 1]) else None


def parse_global_opts(tokens: list[str], base_dir: str) -> tuple[str, bool, list[str]]:
    """Returns (effective_dir, trusted, remaining_tokens_from_subcommand)."""
    i = 1  # tokens[0] == "git"
    dir_ = base_dir
    trusted = True
    while i < len(tokens):
        token = tokens[i]
        if token in GLOBAL_VALUE_OPTS:
            if i + 1 >= len(tokens):
                raise ParseError("git global option missing a value")
            value = tokens[i + 1]
            if token == "-C":
                dir_ = value if os.path.isabs(value) else os.path.join(dir_, value)
            else:
                trusted = False
            i += 2
            continue
        long_opt = next(
            (
                opt
                for opt in GLOBAL_VALUE_OPTS
                if opt.startswith("--") and token.startswith(opt + "=")
            ),
            None,
        )
        if long_opt is not None:
            trusted = False
            i += 1
            continue
        if token in GLOBAL_FLAGS:
            i += 1
            continue
        if token.startswith(("-C", "-c")) and len(token) > 2:
            value = token[2:]
            if token.startswith("-C"):
                dir_ = value if os.path.isabs(value) else os.path.join(dir_, value)
            else:
                trusted = False
            i += 1
            continue
        break
    return dir_, trusted, tokens[i:]


def is_short_force_cluster(arg: str) -> bool:
    """A combined short-option cluster like -f, -fd, -xfd (never --long)."""
    return arg.startswith("-") and not arg.startswith("--") and "f" in arg[1:]


def is_branch_force_delete_cluster(arg: str) -> bool:
    """-D, or a combined short cluster with both d (delete) and f (force),
    such as -fd/-df/-Df - git-branch bundles short options like these."""
    if not (arg.startswith("-") and not arg.startswith("--")):
        return False
    letters = arg[1:]
    return "D" in letters or ("d" in letters and "f" in letters)


def classify(subcommand: str, args: list[str]) -> tuple[str, list[str] | str | None]:
    """Evaluates one git subcommand's argv against the destructive-op
    table. Returns (kind, info):

        safe              info=None
        block             info=human-readable rule text
        cleanup-branch     info=branch names to verify as merged
        cleanup-worktree    info=the worktree path to verify as merged
    """
    if subcommand == "reset":
        if "--hard" in args:
            return "block", "git reset --hard"
        return "safe", None
    if subcommand == "clean":
        if "--force" in args or any(is_short_force_cluster(a) for a in args):
            return "block", "git clean --force"
        return "safe", None
    if subcommand == "branch":
        wants_force_delete = (
            "-D" in args
            or ("--delete" in args and "--force" in args)
            or any(is_branch_force_delete_cluster(a) for a in args)
        )
        if not wants_force_delete:
            return "safe", None
        names = [a for a in args if a not in ("-D", "--delete", "--force")]
        if not names or any(a.startswith("-") for a in names):
            return "block", "git branch -D (unparseable arguments)"
        return "cleanup-branch", names
    if subcommand == "checkout":
        if (
            "--force" in args
            or "." in args
            or any(is_short_force_cluster(a) for a in args)
        ):
            return "block", "git checkout --force or checkout ."
        return "safe", None
    if subcommand == "switch":
        if "-C" in args or "--force-create" in args:
            return "block", "git switch --force-create"
        if (
            "--discard-changes" in args
            or "--force" in args
            or any(is_short_force_cluster(a) for a in args)
        ):
            return "block", "git switch --discard-changes"
        return "safe", None
    if subcommand == "restore":
        if "." in args:
            return "block", "git restore . (or --source ... .)"
        return "safe", None
    if subcommand == "worktree":
        if args[:1] != ["remove"]:
            return "safe", None
        sub_args = args[1:]
        forces = [a for a in sub_args if a in ("-f", "--force")]
        paths = [a for a in sub_args if a not in ("-f", "--force")]
        if not forces:
            return "safe", None
        # One force only: a second one overrides a worktree lock, and a
        # lock means someone asked for the worktree to stay.
        if len(forces) != 1 or len(paths) != 1 or paths[0].startswith("-"):
            return "block", "git worktree remove --force (unparseable arguments)"
        return "cleanup-worktree", paths[0]
    if subcommand == "push":
        if any(a == "--force" or is_short_force_cluster(a) for a in args):
            return "block", "git push --force"
        if any(a.startswith("+") for a in args):
            return "block", "git push +refspec"
        return "safe", None
    return "safe", None


def run_git(directory: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", directory, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def remote_default_branch(directory: str) -> str | None:
    result = run_git(directory, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    if result.returncode == 0:
        return result.stdout.strip()
    for ref in ("refs/remotes/origin/main", "refs/remotes/origin/master"):
        if run_git(directory, "rev-parse", "--verify", "-q", ref).returncode == 0:
            return ref
    return None


def commit_is_merged(directory: str, rev: str) -> bool:
    """True when <rev> is an ancestor of origin's default branch, or was
    squash-merged into it (detected offline by patch-id via `git cherry`)."""
    base = remote_default_branch(directory)
    if base is None:
        return False
    if run_git(directory, "merge-base", "--is-ancestor", rev, base).returncode == 0:
        return True
    merge_base = run_git(directory, "merge-base", base, rev)
    if merge_base.returncode != 0:
        return False
    probe = run_git(
        directory,
        "commit-tree",
        f"{rev}^{{tree}}",
        "-p",
        merge_base.stdout.strip(),
        "-m",
        "guardrails-squash-probe",
    )
    if probe.returncode != 0:
        return False
    cherry = run_git(directory, "cherry", base, probe.stdout.strip())
    if cherry.returncode != 0 or not cherry.stdout:
        return False
    return cherry.stdout.splitlines()[0].startswith("-")


def branch_checked_out_elsewhere(
    porcelain: str, branch: str, removed_worktrees: set[str]
) -> bool:
    """True if `branch` is checked out in a worktree this same command has
    not already been verified to remove (`worktree remove --force ...`
    earlier in the same command frees the branch up for a later delete,
    exactly like running the two commands one after another would)."""
    marker = f"branch refs/heads/{branch}"
    for block in porcelain.split("\n\n"):
        lines = block.splitlines()
        if marker not in lines:
            continue
        path_line = next(
            (
                line[len("worktree ") :]
                for line in lines
                if line.startswith("worktree ")
            ),
            None,
        )
        if path_line is not None and os.path.realpath(path_line) in removed_worktrees:
            continue
        return True
    return False


def branch_is_merged(directory: str, branch: str, removed_worktrees: set[str]) -> bool:
    exists = run_git(directory, "rev-parse", "--verify", "-q", f"refs/heads/{branch}")
    if exists.returncode != 0:
        return False
    worktrees = run_git(directory, "worktree", "list", "--porcelain")
    if worktrees.returncode != 0:
        return False
    if branch_checked_out_elsewhere(worktrees.stdout, branch, removed_worktrees):
        return False
    return commit_is_merged(directory, f"refs/heads/{branch}")


def worktree_is_merged(directory: str, path: str) -> str | None:
    """Returns the worktree's realpath when it is safe to remove (merged,
    no tracked changes), so the caller can also treat it as already gone
    for a later `branch -D` in the same command. None otherwise."""
    full = path if os.path.isabs(path) else os.path.join(directory, path)
    if not os.path.isdir(full):
        return None
    status = run_git(full, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0 or status.stdout.strip():
        return None
    if not commit_is_merged(full, "HEAD"):
        return None
    return os.path.realpath(full)


# hook-config.json's block_patterns predate this rewrite and are documented
# and tested with bash/POSIX ERE syntax (e.g. "git[[:space:]]+status"),
# which Python's `re` does not understand natively. Translate the common
# POSIX bracket classes so existing configs keep working unchanged.
POSIX_CLASSES = {
    "[:alpha:]": r"a-zA-Z",
    "[:digit:]": r"0-9",
    "[:alnum:]": r"a-zA-Z0-9",
    "[:space:]": r"\s",
    "[:upper:]": r"A-Z",
    "[:lower:]": r"a-z",
    "[:blank:]": r" \t",
    "[:punct:]": r"!-/:-@\[-`{-~",
    "[:xdigit:]": r"0-9A-Fa-f",
    "[:cntrl:]": r"\x00-\x1f\x7f",
    "[:print:]": r"\x20-\x7e",
    "[:graph:]": r"\x21-\x7e",
}


def translate_posix_classes(pattern: str) -> str:
    for posix, replacement in POSIX_CLASSES.items():
        pattern = pattern.replace(posix, replacement)
    return pattern


def load_patterns(raw: str) -> list[tuple[re.Pattern[str], str]]:
    """Returns (compiled, original_text) pairs so a match can still show
    the user's own config text rather than its POSIX-class translation."""
    patterns = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            patterns.append((re.compile(translate_posix_classes(line)), line))
        except re.error:
            print(
                f"git-guardrails: skipping invalid block pattern: {line}",
                file=sys.stderr,
            )
    return patterns


def evaluate_git_call(
    git_tokens: list[str],
    ctx: Ctx,
    patterns: list[tuple[re.Pattern[str], str]],
    allow_force_push: bool,
    blocks: list[tuple[str, bool]],
    removed_worktrees: set[str],
) -> None:
    """git_tokens[0] == "git"; the rest runs to the end of its statement."""
    directory, trusted, remaining = parse_global_opts(git_tokens, ctx.cwd)
    overall_trusted = ctx.trusted and trusted
    if not remaining:
        return
    subcommand, args = remaining[0], remaining[1:]

    statement_text = "git " + " ".join(remaining)
    for compiled, original in patterns:
        if allow_force_push and "push" in original:
            continue
        if compiled.search(statement_text):
            blocks.append((original, subcommand in CLEANUP_SUBCOMMANDS))

    if subcommand == "push" and allow_force_push:
        return

    kind, info = classify(subcommand, args)
    is_cleanup_subcommand = subcommand in CLEANUP_SUBCOMMANDS
    if kind == "safe":
        return
    if kind == "block":
        blocks.append((str(info), is_cleanup_subcommand))
        return
    if kind == "cleanup-branch":
        names = info if isinstance(info, list) else []
        if overall_trusted and all(
            branch_is_merged(directory, name, removed_worktrees) for name in names
        ):
            return
        blocks.append((f"git branch -D {' '.join(names)}", True))
        return
    if kind == "cleanup-worktree":
        path = str(info)
        resolved = worktree_is_merged(directory, path) if overall_trusted else None
        if resolved is not None:
            removed_worktrees.add(resolved)
            return
        blocks.append((f"git worktree remove --force {path}", True))
        return


SUBST_OPENER = re.compile(r"^.*(?:\$\(|`|<\(|>\()")


def trim_grouping_chars(span: list[str]) -> list[str]:
    """Drops a leading "("/"{" glued to the first token and a trailing
    ")"/"}" glued to the last, e.g. `(git reset --hard)` after splitting
    on separators is `["(git", "reset", "--hard)"]` - shlex has no notion
    of shell grouping, so these punctuation chars stay stuck to words."""
    span = list(span)
    if span and span[0][:1] in ("(", "{"):
        span[0] = span[0][1:]
    if span and span[-1][-1:] in (")", "}", "`"):
        span[-1] = span[-1][:-1]
    return span


def walk(
    tokens: list[str],
    ctx: Ctx,
    patterns: list[tuple[re.Pattern[str], str]],
    allow_force_push: bool,
    depth: int,
    blocks: list[tuple[str, bool]],
    removed_worktrees: set[str],
) -> None:
    for raw_span in split_statements(tokens):
        span = trim_grouping_chars(raw_span)
        if not span:
            continue

        # cd/pushd/popd only matters as the statement's own command, behind
        # at most the known wrapper keywords - an unrecognized wrapper
        # (e.g. `nice cd x`) just leaves cwd untracked, which only makes
        # later verification more conservative, never less safe.
        i = 0
        while i < len(span) and (
            span[i] in STRIP_PREFIXES or VAR_ASSIGNMENT.match(span[i])
        ):
            i += 1
        head_rest = span[i:]
        head_base = head_rest[0].rsplit("/", 1)[-1] if head_rest else ""
        if head_base in ("cd", "pushd", "popd"):
            handle_cd(head_base, head_rest, ctx)
            continue

        # A git invocation is detected by scanning every token position, not
        # only recognized command-start positions: any wrapper this parser
        # doesn't know (nice, timeout N, strace, ...) must not be able to
        # hide git from evaluation. `eval` and `bash|sh|zsh|dash -c` are the
        # two places a *quoted* command reaches this parser as one token
        # instead of separate words, so their argument gets tokenized too -
        # ordinary quoted arguments (a commit message, a heredoc body) do
        # not, so they stay allowed.
        for j, token in enumerate(span):
            # `$(git`, `` `git ``, `<(git`, and `X=$(git` are one shlex token;
            # command substitution still runs git, so look past the opener.
            base = SUBST_OPENER.sub("", token).rsplit("/", 1)[-1]
            # Case-insensitive: `GIT`, `/usr/bin/GIT`, and `./GIT` all run the
            # real git binary on macOS's case-insensitive filesystem. `eval`
            # is a shell builtin (resolved by bash's own keyword table, never
            # the filesystem), so it stays case-sensitive on purpose.
            if base.lower() == "git":
                evaluate_git_call(
                    span[j:], ctx, patterns, allow_force_push, blocks, removed_worktrees
                )
                break
            if depth == 0 and base == "eval":
                nested = " ".join(span[j + 1 :])
                if nested:
                    inner = tokenize(strip_heredocs(nested))
                    walk(
                        inner,
                        ctx.copy(),
                        patterns,
                        allow_force_push,
                        depth + 1,
                        blocks,
                        removed_worktrees,
                    )
                break
            if depth == 0 and base.lower() in INTERPRETERS:
                script = shell_dash_c_script(span, j)
                if script is not None:
                    inner = tokenize(strip_heredocs(script))
                    walk(
                        inner,
                        ctx.copy(),
                        patterns,
                        allow_force_push,
                        depth + 1,
                        blocks,
                        removed_worktrees,
                    )
                    break


def decide(
    command: str,
    cwd: str,
    allow_force_push: bool,
    patterns: list[tuple[re.Pattern[str], str]],
) -> tuple[str, bool] | None:
    tokens = tokenize(strip_heredocs(command))
    ctx = Ctx(cwd, True)
    blocks: list[tuple[str, bool]] = []
    walk(tokens, ctx, patterns, allow_force_push, 0, blocks, set())
    return blocks[0] if blocks else None


def main() -> None:
    command = os.environ.get("GG_COMMAND", "")
    cwd = os.environ.get("GG_CWD") or os.getcwd()
    allow_force_push = os.environ.get("GG_ALLOW_FORCE_PUSH") == "1"
    patterns = load_patterns(os.environ.get("GG_PATTERNS", ""))

    try:
        result = decide(command, cwd, allow_force_push, patterns)
    except ParseError:
        result = ("could not safely parse this command (failing closed)", False)

    if result is None:
        print("ALLOW")
        return
    rule, cleanup_hint = result
    print("BLOCK")
    print(rule)
    print("1" if cleanup_hint else "0")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - fail closed on any bug, never silently allow
        print("BLOCK")
        print(f"internal error while analyzing this command: {exc}")
        print("0")
