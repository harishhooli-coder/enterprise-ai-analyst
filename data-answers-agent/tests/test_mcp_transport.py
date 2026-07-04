"""Tests for MCP warehouse transport."""

from app.config import get_settings
from app.identity.stub_broker import StubIdentityBroker
from app.models import ExecutionContext, UserPrincipal, WarehouseResult
from app.tools.mcp_client import set_mcp_client_factory
from app.tools.warehouse import query_warehouse


def test_query_warehouse_routes_through_mcp(monkeypatch):
    monkeypatch.setenv("USE_MCP", "1")
    get_settings.cache_clear()

    captured: dict = {}

    def fake_mcp(
        template_sql: str,
        params: dict[str, str],
        execution_context: ExecutionContext,
        metric_id: str,
    ) -> WarehouseResult:
        captured["template_sql"] = template_sql
        captured["params"] = params
        captured["metric_id"] = metric_id
        return WarehouseResult(
            rows=[{"total_revenue": 1_250_000.0}],
            bytes_scanned=100,
            template_id=metric_id,
            executing_identity_id=execution_context.executing_identity_id,
        )

    set_mcp_client_factory(fake_mcp)
    ctx = StubIdentityBroker().mint(
        UserPrincipal(user_id="u1", allowed_regions=["US", "EU"]),
    )
    try:
        result = query_warehouse(
            "SELECT 1",
            {"month": "2026-06"},
            ctx,
            metric_id="total_revenue",
        )
    finally:
        set_mcp_client_factory(None)
        get_settings.cache_clear()

    assert captured["metric_id"] == "total_revenue"
    assert result.rows[0]["total_revenue"] == 1_250_000.0
