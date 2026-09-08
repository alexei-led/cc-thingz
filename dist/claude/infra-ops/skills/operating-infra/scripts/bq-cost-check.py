#!/usr/bin/env python3
"""Estimate BigQuery query cost before running.

Usage: bq-cost-check.py "SELECT * FROM table"
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys

BQ_TIMEOUT_SECS = 120

# Matches bq's dry-run prose: "...will process 1,234 bytes of data." Anchored
# on "process ... bytes" so a version banner or job id elsewhere in the output
# can't be mistaken for the byte count.
BYTES_PROSE_RE = re.compile(r"process\s+([\d,]+)\s+bytes", re.IGNORECASE)


def estimate_bytes(query: str, location: str | None = None) -> int:
    try:
        result = subprocess.run(
            [
                "bq",
                *([f"--location={location}"] if location else []),
                "query",
                "--dry_run",
                "--use_legacy_sql=false",
                "--format=json",
                query,
            ],
            capture_output=True,
            text=True,
            timeout=BQ_TIMEOUT_SECS,
        )
    except FileNotFoundError:
        raise SystemExit("Error: bq CLI is not installed") from None
    except subprocess.TimeoutExpired:
        raise SystemExit(
            f"Error: bq dry-run timed out after {BQ_TIMEOUT_SECS}s"
        ) from None
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit("Error: bq dry-run failed")

    # `bq query --dry_run` prints job metadata to stderr; --format=json gives
    # an empty list on stdout. The byte count surfaces in stderr text:
    #   "Query successfully validated. Assuming the tables are not modified,
    #    running this query will process N bytes of data."
    # Newer bq versions also support --format=prettyjson with totalBytesProcessed
    # in stderr-rendered JSON. We parse both.
    def find(obj: object) -> int | None:
        if isinstance(obj, dict):
            if "totalBytesProcessed" in obj:
                value = obj["totalBytesProcessed"]
                if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
                    raise SystemExit("Error: invalid totalBytesProcessed in bq output")
                return int(value)
            for value in obj.values():
                hit = find(value)
                if hit is not None:
                    return hit
        elif isinstance(obj, list):
            for value in obj:
                hit = find(value)
                if hit is not None:
                    return hit
        return None

    for blob in (result.stdout, result.stderr):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            match = BYTES_PROSE_RE.search(blob)
            if match:
                return int(match.group(1).replace(",", ""))
        else:
            value = find(data)
            if value is not None:
                return value
    raise SystemExit(
        "Error: could not parse bq output:\n" + result.stdout + result.stderr
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run a query; report bytes and optional cost."
    )
    parser.add_argument("query")
    parser.add_argument("--location", help="BigQuery job location")
    parser.add_argument("--price-per-tib", type=float, help="Explicit USD per TiB rate")
    parser.add_argument("--max-bytes", type=int, help="Exit 1 above this byte count")
    parser.add_argument(
        "--max-usd", type=float, help="Exit 1 above this estimated USD cost"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    for name in ("price_per_tib", "max_bytes", "max_usd"):
        value = getattr(args, name)
        if value is not None and (value < 0 or not math.isfinite(value)):
            parser.error(f"--{name.replace('_', '-')} must be finite and nonnegative")
    if args.max_usd is not None and args.price_per_tib is None:
        parser.error("--max-usd requires --price-per-tib")

    n = estimate_bytes(args.query, args.location)
    cost = n / 1024**4 * args.price_per_tib if args.price_per_tib is not None else None
    exceeded = (args.max_bytes is not None and n > args.max_bytes) or (
        args.max_usd is not None and cost is not None and cost > args.max_usd
    )
    if args.json:
        print(
            json.dumps(
                {
                    "bytes_processed": n,
                    "location": args.location,
                    "price_per_tib_usd": args.price_per_tib,
                    "estimated_cost_usd": cost,
                    "threshold_exceeded": exceeded,
                }
            )
        )
    else:
        print(f"Query will scan: {n} bytes ({n / 1024**3:.2f} GiB)")
        if cost is not None:
            print(f"Estimated cost: ${cost:.4f} at ${args.price_per_tib:g}/TiB")
            print("Estimate excludes free tiers, discounts, and capacity pricing.")
        if exceeded:
            print("Threshold exceeded", file=sys.stderr)
    return 1 if exceeded else 0


if __name__ == "__main__":
    sys.exit(main())
