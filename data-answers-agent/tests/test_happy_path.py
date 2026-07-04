from tests.conftest import assert_audit_record_exists


def test_happy_path(client, valid_principal, mock_warehouse, audit_sink_access):
    response = client.post(
        "/ask",
        json={
            "question": "What was total revenue last month?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["source"] == "total_revenue"
    assert body["data"]["confidence"] >= 0
    assert body["data"]["resolved_interpretation"]
    assert "SELECT" not in body["data"]["answer"].upper()
    assert body["request_id"]

    record = assert_audit_record_exists(audit_sink_access, body["request_id"])
    assert record["grounding_status"] == "match"
    assert record["metric_id"] == "total_revenue"
    assert record["policy_decision"] == "allow"
    assert record["response_status"] == "ok"
    assert record["bytes_scanned"] >= 0
