---
name: bigquery-readonly-warehouse
description: >-
  Read-only BigQuery warehouse tool patterns for the Data-Answers Agent.
  Use when implementing query_warehouse, parameterized SQL templates,
  maximum_bytes_billed, row-filter stubs, or mocking BigQuery in tests.
---

# BigQuery Read-Only Warehouse Tool

## Package

`google-cloud-bigquery` — official client. Auth via `GOOGLE_APPLICATION_CREDENTIALS` or ADC.

## Tool signature

```python
def query_warehouse(
    template: VerifiedQueryTemplate,
    params: dict[str, str],
    principal: UserPrincipal,
) -> list[dict]:
    ...
```

## Non-negotiable requirements

1. **Parameterized only** — bind `{month}`, `{region_filter}` slots; never concatenate user question text into SQL
2. **`maximum_bytes_billed`** on every `QueryJobConfig`
3. **Read-only guard** — reject templates containing write verbs before execution
4. **Identity stub** — inject row filter from `principal.allowed_regions`
5. **Audit** — log template id, params (safe), bytes scanned, executing identity

## Write-verb guard

```python
WRITE_VERBS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

def assert_readonly(sql: str) -> None:
    if WRITE_VERBS.search(sql):
        raise ReadOnlyViolationError("Template contains write verb")
```

## Parameter binding (safe)

Use BigQuery query parameters, not f-strings with user input:

```python
from google.cloud import bigquery

job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("month", "STRING", params["month"]),
    ],
    maximum_bytes_billed=settings.max_bytes_billed,
)
```

For `{region_filter}` stub, build from principal server-side:

```python
def region_filter_clause(regions: list[str]) -> str:
    if not regions:
        return "1=0"  # deny-all when no regions
    quoted = ", ".join(f"'{r}'" for r in regions)
    return f"region IN ({quoted})"
```

Leave at seam:

```python
# TODO(harden): replace stub row-filter with BigQuery RLS via WIF/impersonation
```

## Mocking in CI

Inject a `WarehouseClient` protocol; tests use a fake returning canned rows. Never require live BQ in CI.

## Config env vars

- `BQ_PROJECT_ID`, `BQ_DATASET`, `MAX_BYTES_BILLED` (e.g. `1000000000` = 1 GB cap)

## Common mistakes (avoid)

- f-string SQL with user question text
- Missing bytes cap
- Single service account that reads everything (thread principal even if cred is shared in dev)
- Returning raw SQL or table names to the caller (audit only)
