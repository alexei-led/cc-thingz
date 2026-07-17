#!/usr/bin/env bash
# smart-lint.sh - concise project-aware format and lint checks.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT=$(cat)

if command -v python3 >/dev/null 2>&1 && python3 -c 'import json,sys
try:
    data=json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(1)
sys.exit(0 if data.get("event") == "post-tool" and isinstance(data.get("piEvent"), dict) else 1)
' <<<"$INPUT"; then
	# Pi's aggregate runtime reserves stdout for its JSON decision envelope.
	# Keep existing diagnostic output on stderr and report a non-blocking result.
	printf '%s' "$INPUT" | bash "$SCRIPT_DIR/smart-lint/main.sh" >&2
	status=$?
	echo '{"decision":"allow"}'
	exit "$status"
fi

# shellcheck source=smart-lint/main.sh
source "$SCRIPT_DIR/smart-lint/main.sh"
