"""Upstash Redis client — HTTP-based, serverless-friendly."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.config import get_settings

if TYPE_CHECKING:
    from upstash_redis import Redis

AUDIT_KEY_PREFIX = "audit:request:"


@lru_cache
def _create_redis_client() -> Redis | None:
    """Return a shared Redis client when Upstash credentials are configured."""
    settings = get_settings()
    if not settings.upstash_redis_rest_url or not settings.upstash_redis_rest_token:
        return None

    from upstash_redis import Redis

    return Redis(
        url=settings.upstash_redis_rest_url,
        token=settings.upstash_redis_rest_token,
    )


def get_redis_client() -> Redis | None:
    return _create_redis_client()


def redis_health() -> dict[str, Any] | None:
    """Ping Redis when configured; return None if Redis is not enabled."""
    client = get_redis_client()
    if client is None:
        return None

    try:
        pong = client.ping()
        return {"status": "ok" if pong == "PONG" else "error"}
    except Exception as exc:  # noqa: BLE001 — health probe must not raise
        return {"status": "error", "detail": str(exc)}


def clear_redis_client_cache() -> None:
    """Reset cached client (for tests after env changes)."""
    _create_redis_client.cache_clear()
