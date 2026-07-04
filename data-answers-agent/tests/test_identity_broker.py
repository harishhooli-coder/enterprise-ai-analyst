"""Tests for identity broker and execution context wiring."""

import pytest

from app.config import get_settings
from app.identity.broker import IdentityConfigurationError, get_identity_broker, set_identity_broker
from app.identity.stub_broker import StubIdentityBroker
from app.identity.wif_broker import WifIdentityBroker
from app.models import ExecutionContext, UserPrincipal
from app.tools.warehouse import query_warehouse, set_bq_client_factory
from tests.conftest import assert_audit_record_exists


@pytest.fixture(autouse=True)
def reset_identity_broker():
    set_identity_broker(None)
    yield
    set_identity_broker(None)


def test_stub_broker_mints_dev_identity():
    broker = StubIdentityBroker()
    principal = UserPrincipal(user_id="u1", allowed_regions=["US"])
    ctx = broker.mint(principal)

    assert ctx.requesting_principal == principal
    assert ctx.executing_identity_type == "stub_dev"
    assert ctx.uses_warehouse_rls is False
    assert "dev-readonly" in ctx.executing_identity_id or "@" in ctx.executing_identity_id


def test_wif_broker_raises_without_config(monkeypatch):
    monkeypatch.setenv("IDENTITY_MODE", "wif")
    monkeypatch.setenv("BQ_IMPERSONATE_TARGET", "")
    monkeypatch.setenv("WIF_PROVIDER_CONFIG", "")
    get_settings.cache_clear()

    broker = WifIdentityBroker()
    principal = UserPrincipal(user_id="u1", allowed_regions=["US"])

    with pytest.raises(IdentityConfigurationError, match="WIF identity mode requires"):
        broker.mint(principal)

    get_settings.cache_clear()


def test_warehouse_applies_row_filter_in_stub_mode():
    captured: dict = {}

    def fake_bq(sql, params, execution_context, max_bytes):
        captured["sql"] = sql
        return [{"total_revenue": 100.0}]

    set_bq_client_factory(fake_bq)
    try:
        ctx = StubIdentityBroker().mint(UserPrincipal(user_id="u1", allowed_regions=["US", "EU"]))
        template = "SELECT 1 FROM t WHERE {region_filter}"
        query_warehouse(template, {}, ctx)
        assert "region IN ('US', 'EU')" in captured["sql"]
    finally:
        set_bq_client_factory(None)


def test_warehouse_skips_row_filter_in_wif_mode():
    captured: dict = {}

    def fake_bq(sql, params, execution_context, max_bytes):
        captured["sql"] = sql
        return [{"total_revenue": 100.0}]

    set_bq_client_factory(fake_bq)
    try:
        ctx = ExecutionContext(
            requesting_principal=UserPrincipal(user_id="u1", allowed_regions=["US"]),
            executing_identity_id="user:alice@corp.com",
            executing_identity_type="federated_user",
            uses_warehouse_rls=True,
        )
        template = "SELECT 1 FROM t WHERE {region_filter}"
        query_warehouse(template, {}, ctx)
        assert "region IN" not in captured["sql"]
        assert "1=1" in captured["sql"]
    finally:
        set_bq_client_factory(None)


def test_audit_records_executing_identity(client, valid_principal, mock_warehouse, audit_sink_access):
    response = client.post(
        "/ask",
        json={
            "question": "What was total revenue last month?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    body = response.json()
    record = assert_audit_record_exists(audit_sink_access, body["request_id"])

    assert record["executing_identity_id"]
    assert record["executing_identity_type"] == "stub_dev"
    assert record["identity_mode"] == "stub"
    assert record["principal"]["user_id"] == valid_principal["user_id"]


def test_end_to_end_identity_in_ask(client, valid_principal, mock_warehouse, audit_sink_access):
    response = client.post(
        "/ask",
        json={
            "question": "What was total revenue last month?",
            "user_principal": valid_principal,
        },
    )
    body = response.json()
    record = assert_audit_record_exists(audit_sink_access, body["request_id"])

    assert record["principal"]["user_id"] == "u1"
    assert record["executing_identity_id"] != record["principal"]["user_id"]
    assert "identity_mint" in [step["step"] for step in record.get("steps", [])]


def test_wif_mode_errors_on_ask_without_config(client, valid_principal, monkeypatch):
    monkeypatch.setenv("IDENTITY_MODE", "wif")
    monkeypatch.setenv("BQ_IMPERSONATE_TARGET", "")
    monkeypatch.setenv("WIF_PROVIDER_CONFIG", "")
    get_settings.cache_clear()
    set_identity_broker(None)

    response = client.post(
        "/ask",
        json={
            "question": "What was total revenue last month?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "WIF identity mode requires" in (body.get("error") or "")

    get_settings.cache_clear()
