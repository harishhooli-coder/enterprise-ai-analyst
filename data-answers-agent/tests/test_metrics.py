"""Tests for Phase 3 evaluation metric hooks."""

from app.observability.metrics import metrics_collector


def test_metrics_endpoint_empty(client):
    metrics_collector.reset()
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["agent_requests_total"] == {}
    assert body["deflection_rate"] == 0.0


def test_metrics_recorded_after_ask(client, valid_principal, mock_warehouse):
    metrics_collector.reset()
    response = client.post(
        "/ask",
        json={
            "question": "What was total revenue last month?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    metrics = client.get("/metrics").json()
    assert metrics["agent_requests_total"]["ok"] == 1
    assert metrics["deflection_rate"] == 1.0
    assert metrics["agent_latency_ms_avg"] >= 0


def test_clarification_increments_clarification_counter(client, valid_principal):
    metrics_collector.reset()
    response = client.post(
        "/ask",
        json={
            "question": "What was revenue last month?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "needs_clarification"

    metrics = client.get("/metrics").json()
    assert metrics["agent_clarifications_total"] == 1
    assert metrics["clarification_rate"] == 1.0
