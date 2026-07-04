"""Integration tests for Neon PostgreSQL warehouse (skipped without DATABASE_URL)."""

import os
from pathlib import Path

import pytest
import yaml

from app.config import get_settings
from app.identity.stub_broker import StubIdentityBroker
from app.models import UserPrincipal
from app.tools.warehouse import query_warehouse

_REGISTRY = Path(__file__).resolve().parents[1] / "app" / "grounding" / "registry.yaml"


@pytest.fixture
def postgres_env(monkeypatch):
    from dotenv import load_dotenv

    load_dotenv(_REGISTRY.parents[2] / ".env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("DATABASE_URL not set")
    monkeypatch.setenv("WAREHOUSE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BQ_USE_MOCK", "0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_postgres_total_revenue_us_eu(postgres_env):
    with _REGISTRY.open(encoding="utf-8") as handle:
        metrics = yaml.safe_load(handle)["metrics"]
    metric = next(m for m in metrics if m["id"] == "total_revenue")
    ctx = StubIdentityBroker().mint(
        UserPrincipal(user_id="u1", allowed_regions=["US", "EU"]),
    )
    result = query_warehouse(
        metric["template"].replace("{project}", "dev-project").replace("{dataset}", "analytics"),
        params={"month": "2026-06"},
        execution_context=ctx,
        metric_id="total_revenue",
    )
    assert result.rows[0]["total_revenue"] == pytest.approx(1_250_000.0, rel=0, abs=1)
