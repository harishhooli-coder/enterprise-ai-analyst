"""Offline golden-set evaluation harness."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import yaml

from app.audit.audit import audit_sink
from app.eval.models import CaseResult, EvalReport, GoldenCase, GoldenSet
from app.identity.broker import set_identity_broker
from app.identity.stub_broker import StubIdentityBroker
from app.loop.orchestrator import orchestrator
from app.models import AskRequest

_DEFAULT_GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_set.yaml"


def load_golden_set(path: Path | None = None) -> GoldenSet:
    golden_path = path or _DEFAULT_GOLDEN_PATH
    with golden_path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return GoldenSet.model_validate(payload)


def _ensure_mock_env() -> None:
    os.environ.setdefault("BQ_PROJECT_ID", "dev-project")
    os.environ.setdefault("BQ_USE_MOCK", "1")
    from app.config import get_settings

    get_settings.cache_clear()


def _evaluate_case(case: GoldenCase, response, audit_record: dict | None) -> CaseResult:
    expect = case.expect
    failures: list[str] = []

    if response.status != expect.status:
        failures.append(f"status: expected {expect.status!r}, got {response.status!r}")

    if expect.source is not None:
        actual_source = response.data.source if response.data else None
        if actual_source != expect.source:
            failures.append(f"source: expected {expect.source!r}, got {actual_source!r}")

    if expect.answer_must_not_contain and response.data and response.data.answer:
        upper = response.data.answer.upper()
        for token in expect.answer_must_not_contain:
            if token.upper() in upper:
                failures.append(f"answer contains forbidden token {token!r}")

    if audit_record is not None:
        if expect.audit_metric_id is not None:
            actual = audit_record.get("metric_id")
            if actual != expect.audit_metric_id:
                failures.append(
                    f"audit metric_id: expected {expect.audit_metric_id!r}, got {actual!r}"
                )
        if expect.audit_grounding_status is not None:
            actual = audit_record.get("grounding_status")
            if actual != expect.audit_grounding_status:
                failures.append(
                    f"audit grounding_status: expected {expect.audit_grounding_status!r}, "
                    f"got {actual!r}"
                )
        if expect.audit_policy_decision is not None:
            actual = audit_record.get("policy_decision")
            if actual != expect.audit_policy_decision:
                failures.append(
                    f"audit policy_decision: expected {expect.audit_policy_decision!r}, "
                    f"got {actual!r}"
                )
    elif any(
        field is not None
        for field in (
            expect.audit_metric_id,
            expect.audit_grounding_status,
            expect.audit_policy_decision,
        )
    ):
        failures.append("missing audit record")

    return CaseResult(
        case_id=case.id,
        passed=len(failures) == 0,
        expected_status=expect.status,
        actual_status=response.status,
        failures=failures,
        request_id=response.request_id,
    )


def run_golden_eval(
    *,
    golden_path: Path | None = None,
    reset_audit: bool = True,
) -> EvalReport:
    """
    Run all golden cases through the orchestrator and score trust metrics.

    Uses mock BigQuery seed data and stub identity (same as CI).
    """
    _ensure_mock_env()
    set_identity_broker(StubIdentityBroker())
    golden = load_golden_set(golden_path)

    if reset_audit:
        audit_sink.clear()

    results: list[CaseResult] = []
    status_counts: dict[str, int] = {}

    for case in golden.cases:
        request_id = str(uuid.uuid4())
        request = AskRequest(question=case.question, user_principal=case.user_principal)
        response = orchestrator.handle(request, request_id)

        audit_records = audit_sink.records_for(request_id)
        audit_record = audit_records[0] if audit_records else None

        result = _evaluate_case(case, response, audit_record)
        results.append(result)
        status_counts[response.status] = status_counts.get(response.status, 0) + 1

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    deflection_rate = round(status_counts.get("ok", 0) / total, 4) if total else 0.0
    clarification_rate = (
        round(status_counts.get("needs_clarification", 0) / total, 4) if total else 0.0
    )
    decline_rate = round(status_counts.get("declined", 0) / total, 4) if total else 0.0

    return EvalReport(
        total=total,
        passed=passed,
        failed=failed,
        deflection_rate=deflection_rate,
        clarification_rate=clarification_rate,
        decline_rate=decline_rate,
        cases=results,
    )
