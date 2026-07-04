"""Read-only, parameterized warehouse tool with optional MCP transport."""

from __future__ import annotations

from typing import Any, Optional

from app.config import get_settings
from app.models import ExecutionContext, WarehouseResult
from app.tools.warehouse_core import (
    ReadOnlyViolationError,
    assert_readonly,
    execute_warehouse_direct,
    get_last_bytes_billed,
    region_filter_clause,
    set_bq_client_factory,
)

__all__ = [
    "ReadOnlyViolationError",
    "assert_readonly",
    "execute_warehouse_direct",
    "get_last_bytes_billed",
    "query_warehouse",
    "region_filter_clause",
    "set_bq_client_factory",
]


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

    Routes through MCP stdio transport when USE_MCP=1; otherwise in-process.
    User question text is never concatenated into SQL — only registry-supplied params bind.
    """
    settings = get_settings()
    if settings.use_mcp_transport:
        from app.tools.mcp_client import query_warehouse_via_mcp

        return query_warehouse_via_mcp(
            template_sql,
            params,
            execution_context,
            metric_id=metric_id,
        )

    return execute_warehouse_direct(
        template_sql,
        params,
        execution_context,
        metric_id=metric_id,
        bq_client=bq_client,
    )
