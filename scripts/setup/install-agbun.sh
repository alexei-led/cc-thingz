#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
version="$(cat "$root/.agentbundler-version")"
if [[ ${1:-} == --canary && $# == 1 ]]; then
	version=latest
elif [[ $# != 0 ]]; then
	echo "Usage: $0 [--canary]" >&2
	exit 2
elif [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "Invalid .agentbundler-version" >&2
	exit 2
fi
go install "github.com/alexei-led/agentbundler/cmd/agbun@$version"
if [[ -n ${GITHUB_PATH:-} ]]; then
	go_bin="$(go env GOPATH)/bin"
	printf '%s\n' "$go_bin" >>"$GITHUB_PATH"
fi
