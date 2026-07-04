---
name: skeleton-testing
description: >-
  pytest patterns for the Data-Answers Agent walking skeleton. Use when writing
  test_happy_path, test_clarification, test_decline, test_readonly_guard, or
  mocking model router and BigQuery in CI.
---

# Skeleton Testing

## Required test files (BUILD-PROMPT acceptance)

| File | Proves |
|------|--------|
| `test_happy_path.py` | Grounded question → `ok` + provenance + audit record |
| `test_clarification.py` | Ambiguous question → `needs_clarification` + audited |
| `test_decline.py` | Out-of-scope / policy deny → `declined` + audited |
| `test_readonly_guard.py` | Write verb in template → rejected; bytes cap set |

## Test stack

```toml
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "httpx>=0.27"]
```

## Fixtures pattern

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def valid_principal():
    return {"user_id": "u1", "allowed_regions": ["US", "EU"]}

@pytest.fixture
def mock_warehouse(monkeypatch):
    def fake_query(template, params, principal):
        return [{"total_revenue": 1_250_000.00}]
    monkeypatch.setattr("app.tools.warehouse.query_warehouse", fake_query)
```

## Mock frontier model in CI

Never call live Anthropic API in CI:

```python
@pytest.fixture(autouse=True)
def mock_model_router(monkeypatch):
    class FakeRouter:
        def classify(self, q): return IntentResult(intent="data_question")
        def reason(self, p): return "Total revenue last month was $1.25M."
    monkeypatch.setattr("app.loop.orchestrator.router", FakeRouter())
```

## Happy path assertion

```python
def test_happy_path(client, valid_principal, mock_warehouse, mock_model_router):
    r = client.post("/ask", json={
        "question": "What was total revenue last month?",
        "user_principal": valid_principal,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["source"] == "total_revenue"
    assert body["data"]["confidence"] >= 0
    assert "SELECT" not in body["data"]["answer"].upper()
    assert_audit_record_exists(body["request_id"])
```

## Readonly guard

```python
def test_rejects_write_template():
    sql = "DELETE FROM sales WHERE 1=1"
    with pytest.raises(ReadOnlyViolationError):
        assert_readonly(sql)
```

## Audit assertion helper

```python
def assert_audit_record_exists(request_id: str):
    records = audit_sink.records_for(request_id)
    assert len(records) == 1
    assert records[0]["principal"]["user_id"]
```

## Rules

- No live BigQuery or Anthropic in CI — mock at tool/router boundaries
- Every test path verifies audit trail
- Test that user-facing answer never contains SQL/table names
- Run: `pytest tests/ -v`
