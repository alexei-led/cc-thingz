#!/usr/bin/env bash
set -euo pipefail

if [ "${HOOK_RELEASE_GUARD:-}" != "1" ]; then
	exit 0
fi

exec python3 "$1"
