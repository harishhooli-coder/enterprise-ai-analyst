"""Tests for seed-data mock warehouse executor."""

from app.grounding.grounding_service import extract_month
from app.identity.stub_broker import StubIdentityBroker
from app.models import ExecutionContext, UserPrincipal
from app.tools.mock_warehouse import execute_mock_query


def _ctx(regions: list[str]) -> ExecutionContext:
    return StubIdentityBroker().mint(
        UserPrincipal(user_id="u1", allowed_regions=regions),
    )


def _last_month() -> str:
    question = "What was revenue last month?"
    month = extract_month(question)
    assert month is not None
    return month


def test_total_revenue_us_eu_last_month():
    ctx = _ctx(["US", "EU"])
    rows, bytes_scanned = execute_mock_query(
        metric_id="total_revenue",
        params={"month": _last_month()},
        execution_context=ctx,
    )
    assert rows[0]["total_revenue"] == 1_250_000.00
    assert bytes_scanned > 0


def test_net_revenue_us_eu_last_month():
    ctx = _ctx(["US", "EU"])
    rows, _ = execute_mock_query(
        metric_id="net_revenue",
        params={"month": _last_month()},
        execution_context=ctx,
    )
    assert rows[0]["net_revenue"] == 980_000.00


def test_order_count_and_aov_us_eu():
    ctx = _ctx(["US", "EU"])
    month = "2026-06"
    count_rows, _ = execute_mock_query(
        metric_id="order_count",
        params={"month": month},
        execution_context=ctx,
    )
    aov_rows, _ = execute_mock_query(
        metric_id="average_order_value",
        params={"month": month},
        execution_context=ctx,
    )
    assert count_rows[0]["order_count"] == 18_400
    assert aov_rows[0]["average_order_value"] == 67.93


def test_active_customers_us_eu():
    ctx = _ctx(["US", "EU"])
    rows, _ = execute_mock_query(
        metric_id="active_customers",
        params={"month": "2026-06"},
        execution_context=ctx,
    )
    assert rows[0]["active_customers"] == 42_500


def test_region_filter_limits_revenue():
    ctx = _ctx(["US"])
    rows, _ = execute_mock_query(
        metric_id="total_revenue",
        params={"month": "2026-06"},
        execution_context=ctx,
    )
    assert rows[0]["total_revenue"] == 750_000.00


def test_no_regions_returns_zero_rows():
    ctx = _ctx([])
    rows, _ = execute_mock_query(
        metric_id="total_revenue",
        params={"month": "2026-06"},
        execution_context=ctx,
    )
    assert rows[0]["total_revenue"] == 0.0


def test_prior_month_differs():
    ctx = _ctx(["US", "EU"])
    rows, _ = execute_mock_query(
        metric_id="total_revenue",
        params={"month": "2026-05"},
        execution_context=ctx,
    )
    assert rows[0]["total_revenue"] == 1_030_000.00
