import pytest

from app.models import UserPrincipal
from app.tools.warehouse import (
    ReadOnlyViolationError,
    assert_readonly,
    get_last_bytes_billed,
    query_warehouse,
    set_bq_client_factory,
)


def test_rejects_write_template():
    sql = "DELETE FROM sales WHERE 1=1"
    with pytest.raises(ReadOnlyViolationError, match="write verb"):
        assert_readonly(sql)


def test_rejects_insert_template():
    sql = "INSERT INTO sales (amount) VALUES (100)"
    with pytest.raises(ReadOnlyViolationError):
        assert_readonly(sql)


def test_bytes_cap_set_on_query():
    captured: dict = {}

    def fake_bq(sql, params, principal, max_bytes):
        captured["max_bytes"] = max_bytes
        return [{"total_revenue": 100.0}]

    set_bq_client_factory(fake_bq)
    try:
        template = (
            "SELECT SUM(amount) AS total_revenue "
            "FROM `proj.ds.sales` WHERE month = @month AND {region_filter}"
        )
        principal = UserPrincipal(user_id="u1", allowed_regions=["US"])
        result = query_warehouse(template, {"month": "2025-06"}, principal, metric_id="total_revenue")
        assert result.rows
        assert captured["max_bytes"] == get_last_bytes_billed()
        assert captured["max_bytes"] > 0
    finally:
        set_bq_client_factory(None)


def test_region_filter_applied_in_query():
    captured: dict = {}

    def fake_bq(sql, params, principal, max_bytes):
        captured["sql"] = sql
        return [{"total_revenue": 100.0}]

    set_bq_client_factory(fake_bq)
    try:
        template = "SELECT 1 FROM t WHERE {region_filter}"
        principal = UserPrincipal(user_id="u1", allowed_regions=["US", "EU"])
        query_warehouse(template, {}, principal)
        assert "region IN ('US', 'EU')" in captured["sql"]
    finally:
        set_bq_client_factory(None)
