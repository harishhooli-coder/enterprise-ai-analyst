"""Golden-set evaluation harness tests."""

import pytest

from app.eval.harness import load_golden_set, run_golden_eval


@pytest.fixture(autouse=True)
def _eval_mock_router(monkeypatch):
    """Match conftest FakeRouter so eval cases behave like integration tests."""
    from app.models import IntentResult

    class FakeRouter:
        def __init__(self):
            self._tokens_used = 0

        @property
        def tokens_used(self):
            return self._tokens_used

        def classify(self, question: str) -> IntentResult:
            self._tokens_used += 50
            q = question.lower()
            if "ignore previous" in q:
                return IntentResult(intent="injection_attempt")
            data_keywords = [
                "revenue",
                "sales",
                "customer",
                "total",
                "month",
                "count",
                "how many",
                "what was",
                "orders",
                "order",
                "active",
                "net",
            ]
            if any(k in q for k in data_keywords):
                return IntentResult(intent="data_question")
            return IntentResult(intent="out_of_scope")

        def reason(self, prompt: str) -> str:
            self._tokens_used += 200
            if "total_revenue" in prompt or "1250000" in prompt or "1,250,000" in prompt:
                return "Total revenue last month was $1.25M."
            return "Here is the answer based on the verified query results."

        def reset_token_count(self):
            self._tokens_used = 0

    fake = FakeRouter()
    monkeypatch.setattr("app.loop.orchestrator.router", fake)


@pytest.fixture(autouse=True)
def _eval_mock_warehouse(monkeypatch):
    monkeypatch.delenv("BQ_USE_MOCK", raising=False)
    monkeypatch.setenv("BQ_PROJECT_ID", "dev-project")
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_golden_set_loads():
    golden = load_golden_set()
    assert len(golden.cases) >= 8
    assert all(case.id and case.question for case in golden.cases)


def test_golden_eval_all_pass():
    report = run_golden_eval()
    assert report.total == len(load_golden_set().cases)
    assert report.failed == 0, [
        (c.case_id, c.failures) for c in report.cases if not c.passed
    ]
    assert report.pass_rate == 1.0


def test_golden_eval_trust_metrics():
    report = run_golden_eval()
    # Golden set is curated: mix of ok, clarify, decline
    assert report.deflection_rate > 0
    assert report.clarification_rate > 0
    assert report.decline_rate > 0
