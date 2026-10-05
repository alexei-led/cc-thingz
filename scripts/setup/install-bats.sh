#!/usr/bin/env bash
# Install Bats 1.14.0 from its release commit, without a shared binary cache.
set -euo pipefail
if [[ $# != 1 ]]; then
	echo "Usage: $0 DESTINATION" >&2
	exit 2
fi
destination="$1"
revision=eb7f42f8d608ac693d7a4b67474f6714ea68cfc5
source_dir="$(mktemp -d)"
trap 'rm -rf "$source_dir"' EXIT
git -C "$source_dir" init --quiet
git -C "$source_dir" fetch --quiet --depth 1 https://github.com/bats-core/bats-core.git "$revision"
git -C "$source_dir" checkout --quiet --detach FETCH_HEAD
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$revision" ]]
"$source_dir/install.sh" "$destination"
"$destination/bin/bats" --version
if [[ -n ${GITHUB_PATH:-} ]]; then
	printf '%s\n' "$destination/bin" >>"$GITHUB_PATH"
fi
