from __future__ import annotations

import time
from typing import Optional

from app.audit.audit import (
    close_record,
    open_record,
    record_bytes,
    record_grounding,
    record_grounding_by_status,
    record_policy,
    record_step,
)
from app.config import get_settings
from app.envelope import (
    ApiResponse,
    clarification_response,
    declined_response,
    error_response,
    ok_response,
)
from app.grounding.grounding_service import grounding_service
from app.loop.model_router import router
from app.models import AnswerPayload, AskRequest
from app.policy.gate import authorize
from app.tools.guardrails import redact_output, scan_input
from app.tools.warehouse import ReadOnlyViolationError, query_warehouse


class Orchestrator:
    """Bounded plan→resolve→authorize→execute→answer loop."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def handle(self, request: AskRequest, request_id: str) -> ApiResponse[AnswerPayload]:
        start = time.monotonic()
        steps = 0
        router.reset_token_count()

        def step(name: str, detail: Optional[dict] = None) -> None:
            nonlocal steps
            steps += 1
            if steps > self._settings.agent_step_cap:
                raise StepCapExceededError("Agent step cap exceeded")
            record_step(request_id, name, detail)

        try:
            # 1. audit-open
            open_record(
                request_id,
                request.user_principal.model_dump(),
                request.question,
            )
            step("audit_open")

            # 2. scan_input
            scan = scan_input(request.question)
            step("scan_input", {"flagged": scan.flagged})
            if scan.flagged:
                record_grounding_by_status(request_id, "declined")
                close_record(
                    request_id,
                    "declined",
                    latency_ms=_elapsed_ms(start),
                    extra={"decline_reason": scan.reason},
                )
                return declined_response(
                    f"Request declined: {scan.reason or 'input flagged'}",
                    request_id,
                )

            # 3. classify
            intent = router.classify(request.question)
            step("classify", {"intent": intent.intent})
            if intent.intent == "injection_attempt":
                close_record(request_id, "declined", latency_ms=_elapsed_ms(start))
                return declined_response("Request declined: suspicious input detected", request_id)
            if intent.intent == "out_of_scope":
                record_grounding_by_status(request_id, "out_of_set")
                close_record(request_id, "declined", latency_ms=_elapsed_ms(start))
                return declined_response("Out of scope, routed to human", request_id)

            self._check_token_budget(request_id)

            # 4. grounding resolve
            grounding = grounding_service.resolve(request.question)
            step("grounding_resolve", {"status": grounding.status})
            record_grounding(request_id, grounding)

            if grounding.status == "ambiguous":
                close_record(
                    request_id,
                    "needs_clarification",
                    latency_ms=_elapsed_ms(start),
                )
                return clarification_response(
                    grounding.clarify_prompt or "Please clarify your question.",
                    request_id,
                )

            if grounding.status == "out_of_set":
                close_record(request_id, "declined", latency_ms=_elapsed_ms(start))
                return declined_response("Out of scope, routed to human", request_id)

            assert grounding.metric_id and grounding.template

            # 5. policy authorize
            decision = authorize(
                request.user_principal,
                grounding.metric_id,
                {"params": grounding.resolved_params},
            )
            step("policy_authorize", {"allowed": decision.allowed, "reason": decision.reason})
            record_policy(request_id, decision.allowed, decision.reason)

            if not decision.allowed:
                close_record(request_id, "declined", latency_ms=_elapsed_ms(start))
                return declined_response(
                    f"Access denied: {decision.reason}",
                    request_id,
                )

            self._check_token_budget(request_id)

            # 6. warehouse query
            result = query_warehouse(
                grounding.template,
                grounding.resolved_params or {},
                request.user_principal,
                metric_id=grounding.metric_id,
            )
            step("warehouse_query", {"rows": len(result.rows), "template_id": result.template_id})
            record_bytes(request_id, result.bytes_scanned)

            self._check_token_budget(request_id)

            # 7. reason / format answer
            value_key = grounding.metric_id
            value = result.rows[0].get(value_key, list(result.rows[0].values())[0]) if result.rows else "N/A"
            reason_prompt = (
                f"Format a concise business answer for metric '{grounding.metric_id}'. "
                f"Question: {request.question}. "
                f"Result value: {value}. "
                f"Do not mention SQL, tables, or schema."
            )
            answer_text = router.reason(reason_prompt)
            step("reason_format")

            self._check_token_budget(request_id)

            resolved = f"Answered '{request.question}' using verified metric '{grounding.metric_id}'"
            payload = AnswerPayload(
                answer=answer_text,
                resolved_interpretation=resolved,
                source=grounding.metric_id,
                confidence=0.85,
            )

            # 8. redact_output
            payload = redact_output(payload)
            step("redact_output")

            # 9. audit-close
            close_record(request_id, "ok", latency_ms=_elapsed_ms(start))
            return ok_response(payload, request_id)

        except StepCapExceededError as exc:
            close_record(
                request_id,
                "error",
                latency_ms=_elapsed_ms(start),
                extra={"error": str(exc)},
            )
            return error_response(str(exc), request_id)

        except TokenBudgetExceededError as exc:
            close_record(
                request_id,
                "error",
                latency_ms=_elapsed_ms(start),
                extra={"error": str(exc)},
            )
            return error_response(str(exc), request_id)

        except ReadOnlyViolationError as exc:
            close_record(
                request_id,
                "error",
                latency_ms=_elapsed_ms(start),
                extra={"error": str(exc)},
            )
            return error_response(str(exc), request_id)

        except Exception as exc:
            close_record(
                request_id,
                "error",
                latency_ms=_elapsed_ms(start),
                extra={"error": str(exc)},
            )
            return error_response(f"Internal error: {exc}", request_id)

    def _check_token_budget(self, request_id: str) -> None:
        if router.tokens_used > self._settings.token_budget:
            raise TokenBudgetExceededError("Token budget exceeded")


class StepCapExceededError(Exception):
    pass


class TokenBudgetExceededError(Exception):
    pass


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


orchestrator = Orchestrator()
