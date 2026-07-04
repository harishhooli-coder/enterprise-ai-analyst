from tests.conftest import assert_audit_record_exists


def test_ambiguous_revenue_needs_clarification(client, valid_principal, audit_sink_access):
    response = client.post(
        "/ask",
        json={
            "question": "What was revenue last month?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["clarification"]
    assert body["data"] is None

    record = assert_audit_record_exists(audit_sink_access, body["request_id"])
    assert record["grounding_status"] == "ambiguous"
    assert record["response_status"] == "needs_clarification"
