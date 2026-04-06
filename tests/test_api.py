from fastapi.testclient import TestClient

from app.api import app


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

    leads = client.get("/admin/leads", headers={"x-admin-token": "change-me"})
    assert leads.status_code == 200
    assert isinstance(leads.json(), list)

    appts = client.get("/admin/appointments", headers={"x-admin-token": "change-me"})
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
    resp = client.get("/admin/stats", headers={"x-admin-token": "change-me"})
    assert resp.status_code == 200
    body = resp.json()
    assert "total_leads" in body
    assert "total_appointments" in body
