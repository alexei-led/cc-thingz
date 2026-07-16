#!/usr/bin/env bash
# Rust linting: rustfmt, cargo clippy, cargo check fallback.

rust_nearest_manifest() {
	local file="$1" dir
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		[[ "$dir" == "." ]] && break
		if [[ -f "$dir/Cargo.toml" ]]; then
			printf '%s\n' "$dir/Cargo.toml"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	[[ -f Cargo.toml ]] && printf '%s\n' "Cargo.toml"
}

rust_manifest_edition() {
	local manifest="$1"
	if command_exists python3; then
		python3 - "$manifest" <<'PY' 2>/dev/null && return 0
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    sys.exit(1)

manifest = Path(sys.argv[1]).resolve()


def load(path: Path):
    try:
        return tomllib.loads(path.read_text())
    except Exception:
        return {}


def direct_edition(data):
    package = data.get("package")
    if not isinstance(package, dict):
        return None
    edition = package.get("edition")
    if isinstance(edition, str) and edition:
        return edition
    if isinstance(edition, dict) and edition.get("workspace") is True:
        return "workspace"
    return None

root_data = load(manifest)
edition = direct_edition(root_data)
if edition and edition != "workspace":
    print(edition)
    sys.exit(0)

if edition == "workspace":
    for parent in [manifest.parent, *manifest.parent.parents]:
        candidate = parent / "Cargo.toml"
        data = load(candidate)
        workspace = data.get("workspace")
        if not isinstance(workspace, dict):
            continue
        package = workspace.get("package")
        if not isinstance(package, dict):
            continue
        value = package.get("edition")
        if isinstance(value, str) and value:
            print(value)
            sys.exit(0)

sys.exit(1)
PY
	fi
	printf '%s\n' "2021"
}

rust_format_files() {
	local files=("$@")
	[[ "${#files[@]}" -gt 0 ]] || return 0
	command_exists rustfmt || return 0

	mark_format_ran
	local file manifest edition output
	for file in "${files[@]}"; do
		manifest=$(rust_nearest_manifest "$file" || true)
		edition="2021"
		if [[ -n "$manifest" ]]; then
			edition=$(rust_manifest_edition "$manifest")
		fi
		if output=$(rustfmt --edition "$edition" "$file" 2>&1); then
			log_debug "rustfmt passed for $file"
		else
			add_error "Rust Formatter (rustfmt) failed for $file" "$(compact_output "$output")"
		fi
	done
}

rust_lint_manifest() {
	local manifest="$1" output
	if output=$(cargo clippy --manifest-path "$manifest" --fix --allow-dirty --allow-staged --all-targets -- -D warnings 2>&1); then
		log_debug "cargo clippy passed for $manifest"
		return 0
	fi

	if echo "$output" | grep -qiE "no such command: .?clippy.?|clippy.*not installed"; then
		log_info "cargo clippy unavailable, falling back to cargo check for $manifest"
		if output=$(cargo check --manifest-path "$manifest" --all-targets 2>&1); then
			log_debug "cargo check passed for $manifest"
		else
			add_error "Rust (cargo check)" "$(compact_output "$output")"
		fi
		return 0
	fi

	add_error "Rust (cargo clippy)" "$(compact_output "$output")"
}

rust_lint_manifests() {
	local files=("$@")
	[[ "${#files[@]}" -gt 0 ]] || return 0
	command_exists cargo || return 0

	local manifests=() manifest tmp
	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-rust-manifests.%s' "$$")
	for file in "${files[@]}"; do
		manifest=$(rust_nearest_manifest "$file" || true)
		[[ -n "$manifest" ]] && printf '%s\n' "$manifest"
	done | sort -u >"$tmp"
	while IFS= read -r manifest; do
		[[ -n "$manifest" ]] && manifests+=("$manifest")
	done <"$tmp"
	rm -f "$tmp"
	[[ "${#manifests[@]}" -gt 0 ]] || return 0

	mark_lint_ran
	for manifest in "${manifests[@]}"; do
		rust_lint_manifest "$manifest"
	done
}

lint_rust() {
	log_debug "rust checks"

	local format_files=()
	while IFS= read -r file; do
		format_files+=("$file")
	done < <(get_changed_files ".rs")

	local lint_inputs=()
	while IFS= read -r file; do
		lint_inputs+=("$file")
	done < <(get_changed_files ".rs" "Cargo.toml" "Cargo.lock" "rust-toolchain" "rust-toolchain.toml")
	if [[ "${#lint_inputs[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Rust files, skipping Rust checks"
		return 0
	fi

	rust_format_files "${format_files[@]}"
	rust_lint_manifests "${lint_inputs[@]}"
}
