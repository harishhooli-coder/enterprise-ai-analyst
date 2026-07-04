"""FastAPI application — POST /ask entry point."""

import uuid

from fastapi import FastAPI

from app.audit.audit import get_audit_sink
from app.envelope import ApiResponse
from app.loop.orchestrator import orchestrator
from app.models import AnswerPayload, AskRequest
from app.observability.metrics import metrics_collector

app = FastAPI(
    title="Data-Answers Agent",
    description="IF-RES-2026-061 walking skeleton — grounded data answers for business users",
    version="0.3.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict:
    """Phase 3 eval hooks — deflection rate, clarification rate, latency averages."""
    return metrics_collector.snapshot()


@app.post("/ask", response_model=ApiResponse[AnswerPayload])
async def ask(body: AskRequest) -> ApiResponse[AnswerPayload]:
    request_id = str(uuid.uuid4())
    result = orchestrator.handle(body, request_id)

    records = get_audit_sink().records_for(request_id)
    record = records[0] if records else {}
    metrics_collector.record_request(
        status=result.status,
        latency_ms=record.get("latency_ms"),
        bytes_scanned=record.get("bytes_scanned"),
        decline_reason=result.decline_reason,
    )
    return result
