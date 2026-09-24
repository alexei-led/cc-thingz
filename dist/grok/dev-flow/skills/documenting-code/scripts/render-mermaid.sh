#!/usr/bin/env bash
# Render each Mermaid diagram in Markdown or .mmd files to PNG for visual review.
#
# Usage: render-mermaid.sh [--out DIR] [--extract] FILE_OR_DIR...
#   --out DIR   write .mmd and .png files to DIR (default: a new temp directory)
#   --extract   only extract the diagrams to .mmd files; do not render
#
# Needs mmdc (@mermaid-js/mermaid-cli) to render. Exit status: 0 all rendered,
# 1 a diagram failed to render, 2 usage error or mmdc missing.
set -euo pipefail

out=""
extract_only=0
inputs=()
while [ $# -gt 0 ]; do
	case "$1" in
	--out)
		out="${2:?--out needs a directory}"
		shift 2
		;;
	--extract)
		extract_only=1
		shift
		;;
	-h | --help)
		sed -n '2,9p' "$0"
		exit 0
		;;
	*)
		inputs+=("$1")
		shift
		;;
	esac
done

if [ ${#inputs[@]} -eq 0 ]; then
	echo "usage: render-mermaid.sh [--out DIR] [--extract] FILE_OR_DIR..." >&2
	exit 2
fi
if [ "$extract_only" -eq 0 ] && ! command -v mmdc >/dev/null 2>&1; then
	echo "mmdc not found: install @mermaid-js/mermaid-cli to render diagrams" >&2
	exit 2
fi
out="${out:-$(mktemp -d "${TMPDIR:-/tmp}/mermaid-render.XXXXXX")}"
mkdir -p "$out"

files=()
for input in "${inputs[@]}"; do
	if [ -d "$input" ]; then
		while IFS= read -r f; do files+=("$f"); done < <(
			find "$input" -type f \( -name '*.md' -o -name '*.mmd' \) \
				-not -path '*/node_modules/*' -not -path '*/.git/*' | sort
		)
	elif [ -f "$input" ]; then
		files+=("$input")
	else
		echo "$input: not found" >&2
		exit 2
	fi
done

diagrams=()
for f in "${files[@]}"; do
	base="$(basename "$f" | sed 's/[^A-Za-z0-9._-]/_/g')"
	if [ "${f##*.}" = "mmd" ]; then
		cp "$f" "$out/$base"
		diagrams+=("$out/$base|$f")
		continue
	fi
	count=$(awk -v out="$out" -v base="${base%.md}" '
		/^[[:space:]]*```mermaid[[:space:]]*$/ { n++; inblock = 1; file = sprintf("%s/%s-%d.mmd", out, base, n); next }
		inblock && /^[[:space:]]*```[[:space:]]*$/ { inblock = 0; close(file); next }
		inblock { print > file }
		END { print n + 0 }
	' "$f")
	for i in $(seq 1 "$count"); do
		diagrams+=("$out/${base%.md}-$i.mmd|$f#$i")
	done
done

if [ ${#diagrams[@]} -eq 0 ]; then
	echo "no Mermaid diagrams found"
	exit 0
fi

failed=0
for entry in "${diagrams[@]}"; do
	mmd="${entry%%|*}"
	src="${entry#*|}"
	if [ "$extract_only" -eq 1 ]; then
		echo "extracted $src -> $mmd"
		continue
	fi
	png="${mmd%.mmd}.png"
	if log=$(mmdc -q -i "$mmd" -o "$png" -b white -s 1.5 2>&1); then
		echo "ok   $src -> $png"
	else
		echo "FAIL $src: $(printf '%s\n' "$log" | grep -m1 -iE 'error|expect' || printf '%s' "$log" | head -1)"
		failed=1
	fi
done
[ "$extract_only" -eq 1 ] || echo "open each PNG and check the layout: rendering proves only that it parses"
exit "$failed"
