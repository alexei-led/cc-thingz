#!/usr/bin/env python3
"""Estimate BigQuery query cost before running.

Usage: bq-cost-check.py "SELECT * FROM table"
"""

from __future__ import annotations

import json
import subprocess
import sys

PRICE_PER_TB = 5.00
WARN_USD = 1.00


def estimate_bytes(query: str) -> int:
    result = subprocess.run(
        [
            "bq",
            "query",
            "--dry_run",
            "--use_legacy_sql=false",
            "--format=json",
            query,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit("Error: bq dry-run failed")

    # `bq query --dry_run` prints job metadata to stderr; --format=json gives
    # an empty list on stdout. The byte count surfaces in stderr text:
    #   "Query successfully validated. Assuming the tables are not modified,
    #    running this query will process N bytes of data."
    # Newer bq versions also support --format=prettyjson with totalBytesProcessed
    # in stderr-rendered JSON. We parse both.
    blob = result.stderr or result.stdout
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        # Fall back to "process <N> bytes" prose
        for token in blob.split():
            if token.isdigit():
                return int(token)
        raise SystemExit("Error: could not parse bq output:\n" + blob) from None

    # Walk JSON for totalBytesProcessed
    def find(obj: object) -> int | None:
        if isinstance(obj, dict):
            if "totalBytesProcessed" in obj:
                return int(obj["totalBytesProcessed"])
            for v in obj.values():
                hit = find(v)
                if hit is not None:
                    return hit
        elif isinstance(obj, list):
            for v in obj:
                hit = find(v)
                if hit is not None:
                    return hit
        return None

    n = find(data)
    if n is None:
        raise SystemExit("Error: totalBytesProcessed missing from bq output")
    return n


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(f"Usage: {sys.argv[0]} <query>", file=sys.stderr)
        return 2

    n = estimate_bytes(args[0])
    gb = n / 1024**3
    tb = n / 1024**4
    cost = tb * PRICE_PER_TB

    print(f"Query will scan: {gb:.2f} GB")
    print(f"Estimated cost: ${cost:.4f}")

    if cost <= WARN_USD:
        return 0

    print(f"WARNING: Query cost exceeds ${WARN_USD:.2f}")
    try:
        reply = input("Continue? (y/N) ")
    except EOFError:
        return 1
    return 0 if reply.strip().lower() in {"y", "yes"} else 1


if __name__ == "__main__":
    sys.exit(main())
