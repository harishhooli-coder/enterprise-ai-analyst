import pytest
from fastapi.testclient import TestClient

from app.audit.audit import audit_sink
from app.loop.model_router import router
from app.main import app
from app.models import IntentResult


@pytest.fixture
def client():
    audit_sink.clear()
    router.reset_token_count()
    return TestClient(app)


@pytest.fixture
def valid_principal():
    return {"user_id": "u1", "allowed_regions": ["US", "EU"]}


@pytest.fixture
def no_regions_principal():
    return {"user_id": "u2", "allowed_regions": []}


@pytest.fixture
def mock_warehouse(monkeypatch):
    def fake_query(template, params, principal, metric_id="unknown"):
        from app.models import WarehouseResult

        stubs = {
            "total_revenue": [{"total_revenue": 1_250_000.00}],
            "net_revenue": [{"net_revenue": 980_000.00}],
            "active_customers": [{"active_customers": 42_500}],
        }
        rows = stubs.get(metric_id, [{"value": 0}])
        return WarehouseResult(rows=rows, bytes_scanned=1024, template_id=metric_id)

    monkeypatch.setattr("app.loop.orchestrator.query_warehouse", fake_query)
    monkeypatch.setattr("app.tools.warehouse.query_warehouse", fake_query)
    return fake_query


@pytest.fixture(autouse=True)
def mock_model_router(monkeypatch):
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
            data_keywords = ["revenue", "sales", "customer", "total", "month", "count", "how many", "what was"]
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
    return fake


@pytest.fixture
def audit_sink_access():
    return audit_sink


def assert_audit_record_exists(audit_sink_access, request_id: str) -> dict:
    records = audit_sink_access.records_for(request_id)
    assert len(records) == 1, f"Expected 1 audit record, got {len(records)}"
    record = records[0]
    assert record["principal"]["user_id"]
    assert record["response_status"] is not None
    return record
