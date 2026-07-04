"""Read-only PostgreSQL warehouse executor for Neon demo deployments."""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings
from app.models import ExecutionContext, WarehouseResult
from app.tools.warehouse_core import assert_readonly, region_filter_clause

# BigQuery-style @param placeholders after _prepare_sql
_PARAM_PATTERN = re.compile(r"@(\w+)")


def prepare_postgres_sql(
    template_sql: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
) -> tuple[str, dict[str, str]]:
    """Convert a BigQuery registry template to parameterized PostgreSQL SQL."""
    assert_readonly(template_sql)
    settings = get_settings()
    schema = settings.bq_dataset

    sql = template_sql.replace("`", "")
    schema_escaped = re.escape(schema)
    sql = re.sub(
        rf"(?:\{{project\}}|[\w-]+)\.(?:\{{dataset\}}|{schema_escaped})\.(\w+)",
        rf"{schema}.\1",
        sql,
    )

    if execution_context.uses_warehouse_rls:
        sql = sql.replace("{region_filter}", "1=1")
    else:
        sql = sql.replace(
            "{region_filter}",
            region_filter_clause(execution_context.requesting_principal.allowed_regions),
        )

    bind_params: dict[str, str] = {}
    for key, value in params.items():
        if "{" + key + "}" in sql:
            sql = sql.replace("{" + key + "}", f"%({key})s")
            bind_params[key] = value

    sql = _PARAM_PATTERN.sub(r"%(\1)s", sql)
    for key, value in params.items():
        if f"%({key})s" in sql:
            bind_params[key] = value

    return sql, bind_params


def execute_postgres_query(
    template_sql: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
    *,
    metric_id: str = "unknown",
) -> WarehouseResult:
    """Execute a vetted registry template against PostgreSQL (Neon demo)."""
    import psycopg
    from psycopg.rows import dict_row

    settings = get_settings()
    sql, bind_params = prepare_postgres_sql(template_sql, params, execution_context)

    # TODO(harden): set app.allowed_regions session var for Postgres RLS when identity_mode=wif
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        with conn.cursor() as cur:
            cur.execute(sql, bind_params)
            rows: list[dict[str, Any]] = list(cur.fetchall())

    bytes_scanned = settings.max_bytes_billed // 10
    return WarehouseResult(
        rows=rows,
        bytes_scanned=bytes_scanned,
        template_id=metric_id,
        executing_identity_id=execution_context.executing_identity_id,
    )
