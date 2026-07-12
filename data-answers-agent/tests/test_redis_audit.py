"""Tests for Upstash Redis audit persistence."""

import json

import pytest

from app.audit.audit import AuditSink
from app.cache.redis_client import AUDIT_KEY_PREFIX, clear_redis_client_cache
from app.config import get_settings
from app.models import UserPrincipal


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.last_ex: int | None = None

    def ping(self) -> str:
        return "PONG"

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        self.last_ex = ex

    def get(self, key: str) -> str | None:
        return self.store.get(key)


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "test-token")
    monkeypatch.setenv("AUDIT_STORE_BACKEND", "redis")
    get_settings.cache_clear()
    clear_redis_client_cache()
    monkeypatch.setattr("app.cache.redis_client.get_redis_client", lambda: client)
    monkeypatch.setattr("app.audit.audit.get_redis_client", lambda: client)
    yield client
    get_settings.cache_clear()
    clear_redis_client_cache()


def test_audit_persists_to_redis(fake_redis):
    sink = AuditSink()
    principal = UserPrincipal(user_id="u1", allowed_regions=["US"])
    sink.open("req-1", principal, "What was revenue?")
    sink.close("req-1", "answered", latency_ms=42)

    key = f"{AUDIT_KEY_PREFIX}req-1"
    assert key in fake_redis.store
    assert fake_redis.last_ex == 604_800

    stored = json.loads(fake_redis.store[key])
    assert stored["request_id"] == "req-1"
    assert stored["response_status"] == "answered"
    assert stored["latency_ms"] == 42


def test_audit_loads_from_redis_when_not_in_memory(fake_redis):
    key = f"{AUDIT_KEY_PREFIX}req-2"
    fake_redis.store[key] = json.dumps(
        {
            "request_id": "req-2",
            "response_status": "declined",
            "principal": {"user_id": "u2", "allowed_regions": ["EU"]},
        }
    )

    sink = AuditSink()
    records = sink.records_for("req-2")
    assert len(records) == 1
    assert records[0]["response_status"] == "declined"


def test_health_includes_redis_when_configured(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "test-token")
    get_settings.cache_clear()
    clear_redis_client_cache()
    monkeypatch.setattr("app.cache.redis_client.get_redis_client", lambda: fake)

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"]["status"] == "ok"

    get_settings.cache_clear()
    clear_redis_client_cache()


def test_health_omits_redis_when_not_configured(client, monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "")
    get_settings.cache_clear()
    clear_redis_client_cache()

    response = client.get("/health")
    assert response.status_code == 200
    assert "redis" not in response.json()

    get_settings.cache_clear()
    clear_redis_client_cache()
