#!/usr/bin/env bash
# Create a git worktree under <project>.worktrees/<branch-slug>.

set -euo pipefail

ALLOW_DIRTY=false
RUN_SETUP=false
RUN_TESTS=false
BASE_REF=""
BRANCH_NAME=""

usage() {
	cat <<'EOF'
Usage: setup-worktree.sh [--base <ref>] [--allow-dirty] [--setup] [--test] <branch-name>

Creates <project>.worktrees/<branch-slug> from the main worktree root.
Refuses dirty current state unless --allow-dirty is passed after user approval.
Existing local and origin branches are checked out instead of recreated.

Options:
  --base <ref>    Base ref for new branches (default: remote default, local main/master/etc, then HEAD)
  --allow-dirty   Proceed even when the current worktree has uncommitted changes
  --setup         Run detected dependency setup after creation
  --test          Run detected baseline test command after creation
EOF
}

while [ "$#" -gt 0 ]; do
	case "$1" in
	--base)
		shift
		[ "$#" -gt 0 ] || {
			echo "Error: --base requires a ref" >&2
			exit 2
		}
		BASE_REF=$1
		shift
		;;
	--base=*)
		BASE_REF=${1#--base=}
		shift
		;;
	--allow-dirty)
		ALLOW_DIRTY=true
		shift
		;;
	--setup)
		RUN_SETUP=true
		shift
		;;
	--test)
		RUN_TESTS=true
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	-*)
		echo "Error: unknown option: $1" >&2
		usage >&2
		exit 2
		;;
	*)
		[ -z "$BRANCH_NAME" ] || {
			echo "Error: branch name already set: $BRANCH_NAME" >&2
			exit 2
		}
		BRANCH_NAME=$1
		shift
		;;
	esac
done

[ -n "$BRANCH_NAME" ] || {
	usage >&2
	exit 2
}

git check-ref-format --branch "$BRANCH_NAME" >/dev/null 2>&1 || {
	echo "Error: invalid branch name: $BRANCH_NAME" >&2
	exit 2
}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
	echo "Error: not in a git repository" >&2
	exit 1
}

if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ] && ! $ALLOW_DIRTY; then
	echo "Error: current worktree is dirty; commit, stash, or re-run with --allow-dirty after approval" >&2
	exit 1
fi

PORCELAIN=$(git -C "$REPO_ROOT" worktree list --porcelain)
MAIN_WT=$(awk '/^worktree /{sub(/^worktree /, ""); print; exit}' <<<"$PORCELAIN")
PROJECT=$(basename "$MAIN_WT")
ROOT="$(dirname "$MAIN_WT")/$PROJECT.worktrees"
SLUG=$(printf '%s' "$BRANCH_NAME" | tr '/' '-')
WORKTREE_PATH="$ROOT/$SLUG"

if [ -e "$WORKTREE_PATH" ]; then
	echo "Error: worktree path already exists: $WORKTREE_PATH" >&2
	exit 1
fi

if grep -Fxq "branch refs/heads/$BRANCH_NAME" <<<"$PORCELAIN"; then
	echo "Error: branch is already checked out in another worktree: $BRANCH_NAME" >&2
	exit 1
fi

has_ref() {
	git -C "$REPO_ROOT" rev-parse --verify --quiet "$1^{commit}" >/dev/null
}

detect_base() {
	local remote_head branch candidate
	remote_head=$(git -C "$REPO_ROOT" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
	if [ -n "$remote_head" ]; then
		branch=${remote_head#origin/}
		if has_ref "$branch"; then
			printf '%s\n' "$branch"
			return 0
		fi
		if has_ref "$remote_head"; then
			printf '%s\n' "$remote_head"
			return 0
		fi
	fi

	for candidate in main master trunk develop dev; do
		if has_ref "$candidate"; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done

	printf 'HEAD\n'
}

if [ -z "$BASE_REF" ]; then
	BASE_REF=$(detect_base)
fi

has_ref "$BASE_REF" || {
	echo "Error: base ref not found: $BASE_REF" >&2
	exit 1
}

mkdir -p "$ROOT"

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
	echo "Checking out existing branch at $WORKTREE_PATH..." >&2
	git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
elif git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME"; then
	echo "Checking out origin/$BRANCH_NAME at $WORKTREE_PATH..." >&2
	git -C "$REPO_ROOT" worktree add --track -b "$BRANCH_NAME" "$WORKTREE_PATH" "origin/$BRANCH_NAME"
else
	echo "Creating worktree at $WORKTREE_PATH from $BASE_REF..." >&2
	git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" "$BASE_REF"
fi

run_setup() {
	cd "$WORKTREE_PATH"
	if [ -f package.json ]; then
		npm install
	elif [ -f go.mod ]; then
		go mod download
	elif [ -f pyproject.toml ]; then
		uv sync
	elif [ -f requirements.txt ]; then
		pip install -r requirements.txt
	elif [ -f Cargo.toml ]; then
		cargo build
	elif [ -x ./gradlew ]; then
		./gradlew testClasses
	elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
		gradle testClasses
	elif [ -x ./mvnw ]; then
		./mvnw -q -DskipTests compile
	elif [ -f pom.xml ]; then
		mvn -q -DskipTests compile
	else
		echo "No known dependency setup detected; skipped." >&2
	fi
}

run_tests() {
	cd "$WORKTREE_PATH"
	if [ -f Makefile ]; then
		make test
	elif [ -f package.json ]; then
		npm test
	elif [ -f go.mod ]; then
		go test ./...
	elif [ -f pyproject.toml ] || [ -d tests ]; then
		pytest
	elif [ -f Cargo.toml ]; then
		cargo test
	elif [ -x ./gradlew ]; then
		./gradlew test
	elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
		gradle test
	elif [ -x ./mvnw ]; then
		./mvnw -q test
	elif [ -f pom.xml ]; then
		mvn -q test
	else
		echo "No known baseline test command detected; skipped." >&2
	fi
}

SETUP_FAILED=false
if $RUN_SETUP; then
	echo "Running dependency setup..." >&2
	run_setup || {
		SETUP_FAILED=true
		echo "warning: dependency setup failed" >&2
	}
fi

if $RUN_TESTS; then
	echo "Running baseline tests..." >&2
	run_tests || echo "warning: baseline tests failed" >&2
fi

cat <<EOF
WORKTREE READY
==============
Branch: $BRANCH_NAME
Path: $WORKTREE_PATH
Base: $BASE_REF

Next:
- cd "$WORKTREE_PATH"
- clean up after PR merge with: scripts/cleanup-worktree.sh "$BRANCH_NAME"
EOF

# Dependency setup failure leaves the worktree unusable for further work
# (missing deps break everything run in it), so the script still reports
# READY with the path an agent needs to fix it manually, but exits non-zero
# to signal the operation needs attention. A failing baseline test suite is
# just information (pre-existing/flaky failures are common) and does not
# block using the worktree, so it only warns and exits 0.
if $SETUP_FAILED; then
	exit 1
fi
