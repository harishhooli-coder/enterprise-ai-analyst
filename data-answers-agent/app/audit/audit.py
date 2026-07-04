"""Structured audit sink — one reconstructable record per request."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from app.models import AllowDeny, ExecutionContext, GroundingResult, UserPrincipal

# TODO(harden): OpenTelemetry span export + durable audit store


def _configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_structlog()
logger = structlog.get_logger(__name__)


class AuditSink:
    """In-memory audit store for tests plus structlog JSON emission."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def open(self, request_id: str, principal: UserPrincipal, question: str) -> None:
        record: dict[str, Any] = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "principal": principal.model_dump(),
            "question": question,
        }
        self._records[request_id] = record
        logger.info("audit.open", **record)

    def record_policy(self, request_id: str, decision: AllowDeny) -> None:
        record = self._records.setdefault(request_id, {"request_id": request_id})
        record["policy_decision"] = "allow" if decision.allowed else "deny"
        record["policy_reason"] = decision.reason
        logger.info(
            "audit.policy",
            request_id=request_id,
            policy_decision=record["policy_decision"],
            policy_reason=decision.reason,
        )

    def record_grounding(self, request_id: str, result: GroundingResult) -> None:
        record = self._records.setdefault(request_id, {"request_id": request_id})
        record["grounding_status"] = result.status
        if result.metric_id is not None:
            record["metric_id"] = result.metric_id
        if result.candidates is not None:
            record["grounding_candidates"] = result.candidates
        if result.resolved_params is not None:
            record["resolved_params"] = result.resolved_params
        logger.info(
            "audit.grounding",
            request_id=request_id,
            grounding_status=result.status,
            metric_id=result.metric_id,
        )

    def close(self, request_id: str, response_status: str, **kwargs: Any) -> None:
        record = self._records.setdefault(request_id, {"request_id": request_id})
        record["response_status"] = response_status
        record["closed_at"] = datetime.now(timezone.utc).isoformat()
        record.update(kwargs)
        logger.info("audit.close", **record)

    def records_for(self, request_id: str) -> list[dict[str, Any]]:
        record = self._records.get(request_id)
        if record is None:
            return []
        return [dict(record)]

    def clear(self) -> None:
        self._records.clear()


_sink = AuditSink()
audit_sink = _sink


def get_audit_sink() -> AuditSink:
    return _sink


def open_record(request_id: str, principal: dict[str, Any], question: str) -> None:
    from app.models import UserPrincipal

    _sink.open(request_id, UserPrincipal.model_validate(principal), question)


def record_step(request_id: str, step: str, detail: dict[str, Any] | None = None) -> None:
    record = _sink._records.setdefault(request_id, {"request_id": request_id})
    steps = record.setdefault("steps", [])
    steps.append({"step": step, "detail": detail or {}})


def record_grounding_by_status(
    request_id: str,
    status: str,
    metric_id: str | None = None,
) -> None:
    record = _sink._records.setdefault(request_id, {"request_id": request_id})
    record["grounding_status"] = status
    if metric_id is not None:
        record["metric_id"] = metric_id


def record_grounding(request_id: str, result: GroundingResult) -> None:
    _sink.record_grounding(request_id, result)


def record_policy(request_id: str, allowed: bool, reason: str) -> None:
    _sink.record_policy(request_id, AllowDeny(allowed=allowed, reason=reason))


def record_bytes(request_id: str, bytes_scanned: int) -> None:
    record = _sink._records.setdefault(request_id, {"request_id": request_id})
    record["bytes_scanned"] = bytes_scanned


def record_executing_identity(request_id: str, context: ExecutionContext) -> None:
    from app.config import get_settings

    record = _sink._records.setdefault(request_id, {"request_id": request_id})
    record["executing_identity_id"] = context.executing_identity_id
    record["executing_identity_type"] = context.executing_identity_type
    record["identity_mode"] = get_settings().identity_mode
    logger.info(
        "audit.identity",
        request_id=request_id,
        executing_identity_id=context.executing_identity_id,
        executing_identity_type=context.executing_identity_type,
        identity_mode=record["identity_mode"],
    )


def close_record(
    request_id: str,
    response_status: str,
    latency_ms: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    kwargs: dict[str, Any] = {}
    if latency_ms is not None:
        kwargs["latency_ms"] = latency_ms
    if extra:
        kwargs.update(extra)
    _sink.close(request_id, response_status, **kwargs)
