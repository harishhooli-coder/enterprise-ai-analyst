from tests.conftest import assert_audit_record_exists


def test_out_of_scope_declined(client, valid_principal, audit_sink_access):
    response = client.post(
        "/ask",
        json={
            "question": "How many unicorns do we have?",
            "user_principal": valid_principal,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "declined"
    assert body["decline_reason"]
    assert "human" in body["decline_reason"].lower() or "scope" in body["decline_reason"].lower()

    record = assert_audit_record_exists(audit_sink_access, body["request_id"])
    assert record["response_status"] == "declined"


def test_no_regions_principal_declined(client, mock_warehouse, no_regions_principal, audit_sink_access):
    response = client.post(
        "/ask",
        json={
            "question": "What was total revenue last month?",
            "user_principal": no_regions_principal,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "declined"
    assert "denied" in body["decline_reason"].lower() or "no_allowed_regions" in body["decline_reason"].lower()

    record = assert_audit_record_exists(audit_sink_access, body["request_id"])
    assert record["policy_decision"] == "deny"
    assert record["response_status"] == "declined"
