"""In-memory success metrics for Phase 3 evaluation hooks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

# TODO(harden): wire OTel exporter + Prometheus /metrics endpoint


@dataclass
class RequestMetrics:
    requests_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    clarifications_total: int = 0
    declines_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_ms_sum: int = 0
    latency_ms_count: int = 0
    bytes_scanned_sum: int = 0
    bytes_scanned_count: int = 0


class MetricsCollector:
    """Thread-safe counters keyed by response status and decline reason."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._metrics = RequestMetrics()

    def record_request(
        self,
        *,
        status: str,
        latency_ms: int | None = None,
        bytes_scanned: int | None = None,
        decline_reason: str | None = None,
    ) -> None:
        with self._lock:
            self._metrics.requests_total[status] += 1
            if status == "needs_clarification":
                self._metrics.clarifications_total += 1
            if status == "declined":
                bucket = (decline_reason or "unspecified")[:80]
                self._metrics.declines_total[bucket] += 1
            if latency_ms is not None:
                self._metrics.latency_ms_sum += latency_ms
                self._metrics.latency_ms_count += 1
            if bytes_scanned is not None:
                self._metrics.bytes_scanned_sum += bytes_scanned
                self._metrics.bytes_scanned_count += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_latency = (
                self._metrics.latency_ms_sum / self._metrics.latency_ms_count
                if self._metrics.latency_ms_count
                else 0.0
            )
            avg_bytes = (
                self._metrics.bytes_scanned_sum / self._metrics.bytes_scanned_count
                if self._metrics.bytes_scanned_count
                else 0.0
            )
            total = sum(self._metrics.requests_total.values())
            answered = self._metrics.requests_total.get("ok", 0)
            deflection_rate = answered / total if total else 0.0
            clarification_rate = (
                self._metrics.clarifications_total / total if total else 0.0
            )

            return {
                "agent_requests_total": dict(self._metrics.requests_total),
                "agent_clarifications_total": self._metrics.clarifications_total,
                "agent_declines_total": dict(self._metrics.declines_total),
                "agent_latency_ms_avg": round(avg_latency, 2),
                "agent_bytes_scanned_avg": round(avg_bytes, 2),
                "deflection_rate": round(deflection_rate, 4),
                "clarification_rate": round(clarification_rate, 4),
            }

    def reset(self) -> None:
        with self._lock:
            self._metrics = RequestMetrics()


metrics_collector = MetricsCollector()
