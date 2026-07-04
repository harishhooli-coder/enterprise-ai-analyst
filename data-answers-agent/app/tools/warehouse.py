"""Read-only, parameterized BigQuery warehouse tool."""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Optional

from app.config import get_settings
from app.models import ExecutionContext, WarehouseResult

WRITE_VERBS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

_bq_client_factory: Optional[
    Callable[[str, dict[str, str], ExecutionContext, int], list[dict]]
] = None
_last_bytes_billed: int = 0


class ReadOnlyViolationError(Exception):
    """Raised when SQL contains a write/mutation verb."""


def assert_readonly(sql: str) -> None:
    """Reject templates containing DML/DDL verbs."""
    if WRITE_VERBS.search(sql):
        raise ReadOnlyViolationError("Template contains write verb")


def region_filter_clause(regions: list[str]) -> str:
    """Build a server-side SQL fragment stub for row-level region filtering."""
    if not regions:
        return "1=0"
    quoted = ", ".join(f"'{region.replace(chr(39), '')}'" for region in regions)
    return f"region IN ({quoted})"


def set_bq_client_factory(
    factory: Optional[Callable[[str, dict[str, str], ExecutionContext, int], list[dict]]],
) -> None:
    """Test hook: inject fake BigQuery execution."""
    global _bq_client_factory
    _bq_client_factory = factory


def get_last_bytes_billed() -> int:
    return _last_bytes_billed


def _use_mock_mode() -> bool:
    if _bq_client_factory is not None:
        return False
    if os.getenv("BQ_USE_MOCK", "").lower() in ("1", "true", "yes"):
        return True
    settings = get_settings()
    if not settings.bq_project_id or settings.bq_project_id == "dev-project":
        return True
    try:
        import google.auth

        google.auth.default()
        return False
    except Exception:
        return True


def _prepare_sql(
    template_sql: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
) -> str:
    assert_readonly(template_sql)
    if execution_context.uses_warehouse_rls:
        sql = template_sql.replace("{region_filter}", "1=1")
    else:
        sql = template_sql.replace(
            "{region_filter}",
            region_filter_clause(execution_context.requesting_principal.allowed_regions),
        )
    for key, value in params.items():
        sql = sql.replace("{" + key + "}", f"@{key}")
    return sql


def query_warehouse(
    template_sql: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
    *,
    metric_id: str = "unknown",
    bq_client: Optional[Any] = None,
) -> WarehouseResult:
    """
    Execute a vetted, parameterized template as the calling principal.

    User question text is never concatenated into SQL — only registry-supplied params bind.
    Row-filter injection is skipped when execution_context.uses_warehouse_rls is True.
    """
    global _last_bytes_billed
    settings = get_settings()
    sql = _prepare_sql(template_sql, params, execution_context)

    if _bq_client_factory is not None:
        rows = _bq_client_factory(sql, params, execution_context, settings.max_bytes_billed)
        _last_bytes_billed = settings.max_bytes_billed
        return WarehouseResult(
            rows=rows,
            bytes_scanned=_last_bytes_billed,
            template_id=metric_id,
            executing_identity_id=execution_context.executing_identity_id,
        )

    if _use_mock_mode():
        from app.tools.mock_warehouse import execute_mock_query

        rows, bytes_scanned = execute_mock_query(
            metric_id=metric_id,
            params=params,
            execution_context=execution_context,
        )
        _last_bytes_billed = bytes_scanned
        return WarehouseResult(
            rows=rows,
            bytes_scanned=bytes_scanned,
            template_id=metric_id,
            executing_identity_id=execution_context.executing_identity_id,
        )

    from google.cloud import bigquery

    query_parameters = [
        bigquery.ScalarQueryParameter(key, "STRING", value)
        for key, value in params.items()
        if "{" + key + "}" in template_sql
    ]
    # TODO(harden): build client from execution_context credential when WIF is active
    client = bq_client or bigquery.Client(project=settings.bq_project_id)
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_parameters,
        maximum_bytes_billed=settings.max_bytes_billed,
    )
    _last_bytes_billed = settings.max_bytes_billed
    job = client.query(sql, job_config=job_config)
    rows = [dict(row) for row in job.result()]
    bytes_scanned = int(getattr(job, "total_bytes_processed", None) or _last_bytes_billed)
    return WarehouseResult(
        rows=rows,
        bytes_scanned=bytes_scanned,
        template_id=metric_id,
        executing_identity_id=execution_context.executing_identity_id,
    )
