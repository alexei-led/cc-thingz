# BigQuery

## Cost safety

- Dry-run before running non-trivial queries.
- Estimate bytes scanned and convert to expected cost when the user asks about cost or the query may be large.
- Use a maximum-bytes-billed guard or equivalent safeguard for exploratory queries.
- Select only needed columns. `LIMIT` does not reduce scan cost.
- Require partition filters for time-partitioned tables unless the user explains why a full scan is needed.
- Prefer clustered filters when they match table design.

## Inspection workflow

- Confirm project, dataset, table, partition field, and date range.
- Inspect schema and partitioning before writing the query.
- For sample data, limit rows and avoid expensive computed fields.
- For exports, confirm destination bucket, format, overwrite behavior, and access controls.

## Safety

- Do not run unbounded all-column queries over large tables.
- Do not write to destination tables until source query, target table, write disposition, and cost are clear.
- Treat DDL/DML, table deletion, and dataset deletion as destructive work requiring exact-resource confirmation.

## Helper

Use `scripts/bq-cost-check.py` when a local BigQuery CLI dry-run cost estimate is useful and the user wants a guard before execution.


The helper performs a dry-run only and never prompts or executes the query:

```bash
uv run python scripts/bq-cost-check.py "SELECT ..." --location <location> --max-bytes <bytes> --json
```

- Default output reports exact processed bytes and GiB.
- Supply `--price-per-tib <USD>` only from an applicable tariff for the project's
  location and billing model; there is no built-in dollar rate.
- `--max-usd <USD>` requires that explicit rate. It is an estimate, not a billing guarantee.
- Exit 1 means a threshold was exceeded or the dry-run failed; exit 2 means invalid arguments.
- This preflight threshold does not enforce the later query's billing limit. Set
  maximum bytes billed on the actual query as well.
