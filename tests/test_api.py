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
