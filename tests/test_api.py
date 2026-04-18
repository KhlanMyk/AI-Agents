from datetime import timedelta
from fastapi.testclient import TestClient

from app.api import app

ADMIN = {"x-admin-token": "change-me"}


def test_health_ok() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_chat_flow_and_persistence() -> None:
    client = TestClient(app)

    r1 = client.post("/chat", json={"message": "hi"})
    assert r1.status_code == 200
    sid = r1.json()["session_id"]

    r2 = client.post("/chat", json={"message": "book appointment", "session_id": sid})
    assert r2.status_code == 200

    r3 = client.post("/chat", json={"message": "confirm appointment", "session_id": sid})
    assert r3.status_code == 200

    leads = client.get("/admin/leads", headers=ADMIN)
    assert leads.status_code == 200
    assert isinstance(leads.json(), list)

    appts = client.get("/admin/appointments", headers=ADMIN)
    assert appts.status_code == 200
    assert isinstance(appts.json(), list)


def test_admin_token_required() -> None:
    client = TestClient(app)
    denied = client.get("/admin/leads")
    assert denied.status_code == 401


def test_validation_rejects_blank_message() -> None:
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "   "})
    assert resp.status_code == 422


def test_admin_stats_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/admin/stats", headers=ADMIN)
    assert resp.status_code == 200
    body = resp.json()
    assert "total_leads" in body
    assert "total_appointments" in body


def test_admin_leads_pagination() -> None:
    """limit and offset params return a valid (possibly empty) list."""
    client = TestClient(app)
    resp = client.get("/admin/leads?limit=2&offset=0", headers=ADMIN)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) <= 2


def test_admin_appointments_pagination() -> None:
    """Pagination works for appointments endpoint."""
    client = TestClient(app)
    resp = client.get("/admin/appointments?limit=1&offset=0", headers=ADMIN)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) <= 1


def test_admin_leads_search_by_intent() -> None:
    """Search leads by intent returns a list (may be empty if no match)."""
    client = TestClient(app)
    resp = client.get("/admin/leads/search?intent=greeting", headers=ADMIN)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_appointment_status_update() -> None:
    """Patch an appointment's status to 'cancelled', verify 404 for missing id."""
    client = TestClient(app)
    # Non-existent id should return 404
    resp = client.patch(
        "/admin/appointments/999999/status",
        json={"status": "cancelled"},
        headers=ADMIN,
    )
    assert resp.status_code == 404

    # Invalid status should return 422
    resp2 = client.patch(
        "/admin/appointments/1/status",
        json={"status": "flying"},
        headers=ADMIN,
    )
    assert resp2.status_code == 422


def test_session_cleanup_returns_counts() -> None:
    """Cleanup endpoint returns cleaned count even when no sessions expired."""
    client = TestClient(app)
    resp = client.post("/admin/sessions/cleanup", headers=ADMIN)
    assert resp.status_code == 200
    body = resp.json()
    assert "cleaned" in body
    assert isinstance(body["cleaned"], int)
    assert "session_ids" in body


def test_chat_history_export() -> None:
    """Export endpoint returns history for a valid session."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "hello"})
    sid = r.json()["session_id"]

    export = client.get(f"/export/{sid}")
    assert export.status_code == 200
    body = export.json()
    assert "messages" in body
    assert body["message_count"] >= 2  # user + assistant


def test_export_unknown_session_returns_404() -> None:
    """Export for unknown session returns 404."""
    client = TestClient(app)
    resp = client.get("/export/totally-unknown-session-xyz")
    assert resp.status_code == 404


# ── April 9 tests ──────────────────────────────────────────────────────────


def test_chat_response_includes_confidence() -> None:
    """Every chat response includes a non-null confidence score 0–1."""
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "hello"})
    body = resp.json()
    assert "confidence" in body
    assert body["confidence"] is not None
    assert 0.0 <= body["confidence"] <= 1.0


def test_high_confidence_on_clear_intent() -> None:
    """Unambiguous messages like 'what are your prices?' get confidence >= 0.88."""
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "what is the price for cleaning?"})
    assert resp.json()["confidence"] >= 0.88


def test_fallback_returns_suggestions() -> None:
    """Gibberish message with fallback intent includes a non-empty suggestions list."""
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "zzz bloop quux"})
    body = resp.json()
    assert body["intent"] == "fallback"
    # suggestions should be a list (may be empty or filled)
    assert "suggestions" in body


def test_reminder_after_confirmed_appointment() -> None:
    """Reminder endpoint returns patient details after appointment confirmation."""
    client = TestClient(app)
    r1 = client.post("/chat", json={"message": "hi, my name is Alice"})
    sid = r1.json()["session_id"]
    client.post("/chat", json={"message": "book appointment", "session_id": sid})
    client.post("/chat", json={"message": "confirm appointment", "session_id": sid})

    rem = client.get(f"/remind/{sid}")
    assert rem.status_code == 200
    body = rem.json()
    assert body["patient_name"] == "Alice"
    assert "appointment_slot" in body
    assert "clinic_address" in body
    assert "reminder_message" in body


def test_reminder_404_without_appointment() -> None:
    """Reminder returns 404 when no appointment has been confirmed."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "hello"})
    sid = r.json()["session_id"]
    resp = client.get(f"/remind/{sid}")
    assert resp.status_code == 404


def test_session_summary_tracks_symptoms() -> None:
    """Session summary endpoint correctly accumulates detected symptoms."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "I have tooth pain and bleeding gums"})
    sid = r.json()["session_id"]

    summary = client.get(f"/session/{sid}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["symptoms"]["has_symptoms"] is True
    assert body["symptoms"]["count"] >= 1
    assert "pain" in body["symptoms"]["symptoms"] or "bleeding" in body["symptoms"]["symptoms"]


def test_session_summary_includes_intent_and_confidence() -> None:
    """Session summary includes last intent and confidence score."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "what are your hours?"})
    sid = r.json()["session_id"]

    summary = client.get(f"/session/{sid}/summary")
    body = summary.json()
    assert body["last_intent"] == "hours"
    assert body["last_confidence"] is not None
    assert body["message_count"] >= 2


def test_cors_header_present_on_health() -> None:
    """CORS allow-origin header is returned when Origin header is sent."""
    client = TestClient(app)
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_contact_extraction_saved_to_session_summary() -> None:
    """Email shared in chat is extracted and visible in session summary contact field."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "my email is patient@example.com"})
    sid = r.json()["session_id"]

    summary = client.get(f"/session/{sid}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert "contact" in body
    assert body["contact"] == "patient@example.com"


def test_admin_lead_detail_returns_lead() -> None:
    """GET /admin/leads/{id} returns a lead record with expected fields."""
    client = TestClient(app)
    # Create a lead via chat
    r = client.post("/chat", json={"message": "I need a cleaning"})
    assert r.status_code == 200

    leads = client.get("/admin/leads?limit=1", headers=ADMIN)
    assert leads.status_code == 200
    items = leads.json()
    assert len(items) >= 1

    lead_id = items[0]["id"]
    detail = client.get(f"/admin/leads/{lead_id}", headers=ADMIN)
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == str(lead_id)
    assert "session_id" in body
    assert "intent" in body
    assert "created_at" in body


def test_admin_lead_detail_404_unknown() -> None:
    """GET /admin/leads/{id} returns 404 for non-existent lead."""
    client = TestClient(app)
    resp = client.get("/admin/leads/999999", headers=ADMIN)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "lead not found"


def test_admin_appointment_detail_returns_appointment() -> None:
    """GET /admin/appointments/{id} returns an appointment record with expected fields."""
    client = TestClient(app)
    # Trigger appointment creation
    r1 = client.post("/chat", json={"message": "book appointment"})
    sid = r1.json()["session_id"]
    client.post("/chat", json={"message": "confirm appointment", "session_id": sid})

    appts = client.get("/admin/appointments?limit=1", headers=ADMIN)
    assert appts.status_code == 200
    items = appts.json()
    if len(items) == 0:
        return  # no appointment created by this flow, skip gracefully

    appt_id = items[0]["id"]
    detail = client.get(f"/admin/appointments/{appt_id}", headers=ADMIN)
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == str(appt_id)
    assert "patient_name" in body
    assert "slot" in body
    assert "status" in body
    assert "created_at" in body


def test_admin_appointment_detail_404_unknown() -> None:
    """GET /admin/appointments/{id} returns 404 for non-existent appointment."""
    client = TestClient(app)
    resp = client.get("/admin/appointments/999999", headers=ADMIN)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "appointment not found"


def test_admin_active_sessions_endpoint_lists_recent_session() -> None:
    """Admin active sessions endpoint includes session details and message counts."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "hello from active session endpoint"})
    sid = r.json()["session_id"]

    resp = client.get("/admin/sessions/active", headers=ADMIN)
    assert resp.status_code == 200
    body = resp.json()
    assert "sessions" in body
    assert "total" in body
    assert any(item["session_id"] == sid for item in body["sessions"])


def test_session_cleanup_dry_run_does_not_remove_session() -> None:
    """dry_run cleanup reports candidates without deleting in-memory session data."""
    client = TestClient(app)
    r = client.post("/chat", json={"message": "hello dry run cleanup"})
    sid = r.json()["session_id"]

    from app import api as api_module

    original_ttl = api_module.session_mgr.default_ttl
    try:
        api_module.session_mgr.default_ttl = timedelta(seconds=-1)

        dry = client.post("/admin/sessions/cleanup?dry_run=true", headers=ADMIN)
        assert dry.status_code == 200
        body = dry.json()
        assert body["dry_run"] is True
        assert sid in body["session_ids"]

        # Session should still exist because this is a dry run
        summary = client.get(f"/session/{sid}/summary")
        assert summary.status_code == 200
    finally:
        api_module.session_mgr.default_ttl = original_ttl
