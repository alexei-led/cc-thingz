# BigQuery

## Cost safety

- Dry-run non-trivial queries first, and convert bytes scanned to cost when the user asks or the query may be large.
- Set maximum bytes billed on exploratory queries.
- Select only needed columns; `LIMIT` does not reduce scan cost.
- Filter on the partition column of time-partitioned tables unless the user explains why a full scan is needed. Use clustered filters when they match the table design.

## Workflow

- Confirm project, dataset, table, partition field, and date range, then read schema and partitioning before writing the query.
- For samples, limit rows and skip expensive computed fields.
- For exports and destination tables, confirm target, format, write disposition or overwrite behavior, access controls, and cost first.
- DDL, DML, and table or dataset deletion are destructive work.

## Cost helper

`scripts/bq-cost-check.py` runs a dry-run only; it never prompts or executes the query:

```bash
uv run python scripts/bq-cost-check.py "SELECT ..." --location <location> --max-bytes <bytes> --json
```

- Default output reports exact processed bytes and GiB.
- `--price-per-tib <USD>` must come from the tariff for the project's location and billing model; there is no built-in rate. `--max-usd` requires it and gives an estimate, not a billing guarantee.
- Exit 1: threshold exceeded or dry-run failed. Exit 2: invalid arguments.
- The preflight does not limit the later query's billing; set maximum bytes billed on that query too.
