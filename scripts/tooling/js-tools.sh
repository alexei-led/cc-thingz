#!/usr/bin/env bash
# Select project-adopted modern JS tooling, then fall back to legacy tools.
# Formatter order: Oxfmt -> Biome -> Prettier. Linter order: Oxlint -> Biome -> ESLint.
# Usage: js-tools.sh format | lint

set -euo pipefail

usage() {
	echo "usage: $0 format|lint" >&2
	exit 2
}

[[ "$#" -eq 1 ]] || usage
MODE="$1"
case "$MODE" in
format | lint) ;;
*) usage ;;
esac

find_local_node_bin() {
	local name="$1" dir="$PWD"
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -x "$dir/node_modules/.bin/$name" ]]; then
			printf '%s\n' "$dir/node_modules/.bin/$name"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	return 1
}

resolve_node_tool() {
	local name="$1" bin
	bin=$(find_local_node_bin "$name" || true)
	if [[ -n "$bin" ]]; then
		printf '%s\n' "$bin"
		return 0
	fi
	command -v "$name" 2>/dev/null || return 1
}

node_tool_configured() {
	local tool="$1" dir="$PWD" marker
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		case "$tool" in
		biome)
			for marker in biome.json biome.jsonc; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		oxfmt)
			for marker in .oxfmtrc .oxfmtrc.json .oxfmtrc.jsonc .oxfmtrc.js .oxfmtrc.mjs .oxfmtrc.cjs .oxfmtrc.ts .oxfmtrc.mts .oxfmtrc.cts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		oxlint)
			for marker in .oxlintrc .oxlintrc.json .oxlintrc.jsonc oxlint.config.json oxlint.config.jsonc oxlint.config.js oxlint.config.mjs oxlint.config.cjs oxlint.config.ts oxlint.config.mts oxlint.config.cts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		eslint)
			for marker in .eslintrc .eslintrc.json .eslintrc.json5 .eslintrc.yaml .eslintrc.yml .eslintrc.js .eslintrc.mjs .eslintrc.cjs eslint.config.js eslint.config.mjs eslint.config.cjs eslint.config.ts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		prettier)
			for marker in .prettierrc .prettierrc.json .prettierrc.json5 .prettierrc.yaml .prettierrc.yml .prettierrc.js .prettierrc.mjs .prettierrc.cjs prettier.config.js prettier.config.mjs prettier.config.cjs prettier.config.ts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		esac
		dir=$(dirname "$dir")
	done
	return 1
}

package_json_mentions_tool() {
	local tool="$1" package_json="" dir="$PWD"
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/package.json" ]]; then
			package_json="$dir/package.json"
			break
		fi
		dir=$(dirname "$dir")
	done
	[[ -n "$package_json" ]] || return 1
	case "$tool" in
	biome) grep -qiE '(@biomejs/biome|"biome"[[:space:]]*:|(^|[[:space:]/;&])biome([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	oxfmt) grep -qiE '("oxfmt"[[:space:]]*:|(^|[[:space:]/;&])oxfmt([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	oxlint) grep -qiE '(@oxc-project/oxlint|"oxlint"[[:space:]]*:|(^|[[:space:]/;&])oxlint([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	eslint) grep -qiE '("eslint"[[:space:]]*:|(^|[[:space:]/;&])eslint([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	prettier) grep -qiE '("prettier"[[:space:]]*:|(^|[[:space:]/;&])prettier([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	*) return 1 ;;
	esac
}

node_tool_adopted() {
	local tool="$1"
	case "$tool" in
	biome | oxfmt | oxlint | eslint | prettier) ;;
	*) return 1 ;;
	esac
	node_tool_configured "$tool" && return 0
	package_json_mentions_tool "$tool"
}

js_roots=()
if find . -maxdepth 1 -type f \( -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.jsx' -o -name '*.ts' -o -name '*.mts' -o -name '*.cts' -o -name '*.tsx' \) -print -quit 2>/dev/null | grep -q .; then
	js_roots+=(.)
fi
while IFS= read -r candidate; do
	if find "$candidate" -type f \( -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.jsx' -o -name '*.ts' -o -name '*.mts' -o -name '*.cts' -o -name '*.tsx' \) \
		-not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/dist/*' -print -quit 2>/dev/null | grep -q .; then
		js_roots+=("${candidate#./}")
	fi
done < <(find . -mindepth 1 -maxdepth 1 -type d \
	-not -name .git -not -name node_modules -not -name dist -not -name build -not -name .venv -print | sort)

js_globs=()
if [[ -n "${js_roots[*]-}" ]]; then
	for root in "${js_roots[@]}"; do
		for extension in js mjs cjs jsx ts mts cts tsx; do
			js_globs+=("$root/**/*.$extension")
		done
	done
fi

run_format() {
	local oxfmt_bin="" biome_bin="" prettier_bin="" formatter="none"
	local oxfmt_project=0 biome_project=0 prettier_project=0
	if [[ -z "${js_roots[*]-}" ]]; then
		echo "JS formatter: skipped (no JS/TS roots)" >&2
		return 0
	fi
	node_tool_adopted oxfmt && oxfmt_project=1
	node_tool_adopted biome && biome_project=1
	node_tool_adopted prettier && prettier_project=1

	if [[ "$oxfmt_project" -eq 1 ]]; then
		oxfmt_bin=$(resolve_node_tool oxfmt || true)
		[[ -n "$oxfmt_bin" ]] && formatter="oxfmt"
	fi
	if [[ "$formatter" == "none" && "$biome_project" -eq 1 ]]; then
		biome_bin=$(resolve_node_tool biome || true)
		[[ -n "$biome_bin" ]] && formatter="biome"
	fi
	if [[ "$formatter" == "none" && "$prettier_project" -eq 1 ]]; then
		prettier_bin=$(resolve_node_tool prettier || true)
		[[ -n "$prettier_bin" ]] && formatter="prettier"
	fi
	if [[ "$formatter" == "none" ]]; then
		oxfmt_bin=$(resolve_node_tool oxfmt || true)
		if [[ -n "$oxfmt_bin" ]]; then
			formatter="oxfmt"
		else
			biome_bin=$(resolve_node_tool biome || true)
			if [[ -n "$biome_bin" ]]; then
				formatter="biome"
			else
				prettier_bin=$(resolve_node_tool prettier || true)
				[[ -n "$prettier_bin" ]] && formatter="prettier"
			fi
		fi
	fi

	case "$formatter" in
	oxfmt)
		echo "JS formatter: oxfmt"
		"$oxfmt_bin" --write "${js_roots[@]}"
		;;
	biome)
		echo "JS formatter: biome"
		"$biome_bin" format --write "${js_roots[@]}"
		;;
	prettier)
		echo "JS formatter: prettier (fallback)"
		"$prettier_bin" --write --no-error-on-unmatched-pattern "${js_globs[@]}"
		;;
	none) echo "JS formatter: skipped (Oxfmt/Biome/Prettier unavailable)" >&2 ;;
	esac
}

run_lint() {
	local biome_bin="" oxlint_bin="" eslint_bin="" linter="none"
	local biome_project=0 oxlint_project=0 eslint_project=0
	if [[ -z "${js_roots[*]-}" ]]; then
		echo "JS linter: skipped (no JS/TS roots)" >&2
		return 0
	fi
	node_tool_adopted biome && biome_project=1
	node_tool_adopted oxlint && oxlint_project=1
	node_tool_adopted eslint && eslint_project=1

	if [[ "$oxlint_project" -eq 1 ]]; then
		oxlint_bin=$(resolve_node_tool oxlint || true)
		[[ -n "$oxlint_bin" ]] && linter="oxlint"
	elif [[ "$biome_project" -eq 1 ]]; then
		biome_bin=$(resolve_node_tool biome || true)
		[[ -n "$biome_bin" ]] && linter="biome"
	elif [[ "$eslint_project" -eq 1 ]]; then
		eslint_bin=$(resolve_node_tool eslint || true)
		[[ -n "$eslint_bin" ]] && linter="eslint"
	fi
	if [[ "$linter" == "none" ]]; then
		oxlint_bin=$(resolve_node_tool oxlint || true)
		if [[ -n "$oxlint_bin" ]]; then
			linter="oxlint"
		else
			biome_bin=$(resolve_node_tool biome || true)
			if [[ -n "$biome_bin" ]]; then
				linter="biome"
			else
				eslint_bin=$(resolve_node_tool eslint || true)
				[[ -n "$eslint_bin" ]] && linter="eslint"
			fi
		fi
	fi

	case "$linter" in
	oxlint)
		echo "JS linter: oxlint"
		"$oxlint_bin" "${js_roots[@]}"
		;;
	biome)
		echo "JS linter: biome"
		"$biome_bin" lint "${js_roots[@]}"
		;;
	eslint)
		echo "JS linter: eslint (fallback)"
		"$eslint_bin" --cache --no-error-on-unmatched-pattern "${js_globs[@]}"
		;;
	none) echo "JS linter: skipped (Oxlint/Biome/ESLint unavailable)" >&2 ;;
	esac
}

case "$MODE" in
format) run_format ;;
lint) run_lint ;;
esac
