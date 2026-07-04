"""FastAPI application — POST /ask entry point."""

import uuid

from fastapi import FastAPI

from app.audit.audit import get_audit_sink
from app.envelope import ApiResponse
from app.loop.orchestrator import orchestrator
from app.models import AnswerPayload, AskRequest

app = FastAPI(
    title="Data-Answers Agent",
    description="IF-RES-2026-061 walking skeleton — grounded data answers for business users",
    version="0.1.0",
)
audit = get_audit_sink()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=ApiResponse[AnswerPayload])
async def ask(body: AskRequest) -> ApiResponse[AnswerPayload]:
    request_id = str(uuid.uuid4())
    audit.open(request_id, body.user_principal, body.question)
    try:
        result = orchestrator.handle(body, request_id)
        audit.close(
            request_id,
            result.status,
            clarification=result.clarification,
            decline_reason=result.decline_reason,
            error=result.error,
        )
        return result
    except Exception as exc:
        audit.close(request_id, "error", error=str(exc))
        return ApiResponse(status="error", error=str(exc), request_id=request_id)
