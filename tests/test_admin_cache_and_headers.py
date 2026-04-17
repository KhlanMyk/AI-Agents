from fastapi.testclient import TestClient

from app.api import app

ADMIN = {"x-admin-token": "change-me"}


def test_health_response_includes_request_id_header() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")


def test_admin_stats_includes_request_id_header() -> None:
    client = TestClient(app)
    resp = client.get("/admin/stats", headers=ADMIN)
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")


def test_lead_list_cache_is_invalidated_after_new_chat() -> None:
    client = TestClient(app)

    before = client.get("/admin/leads?limit=200", headers=ADMIN)
    assert before.status_code == 200
    before_count = len(before.json())

    created = client.post("/chat", json={"message": "hello from cache invalidation test"})
    assert created.status_code == 200

    after = client.get("/admin/leads?limit=200", headers=ADMIN)
    assert after.status_code == 200
    after_items = after.json()
    assert len(after_items) >= before_count + 1


def test_appointment_list_cache_is_invalidated_after_confirmation() -> None:
    client = TestClient(app)

    before = client.get("/admin/appointments?limit=200", headers=ADMIN)
    assert before.status_code == 200
    before_count = len(before.json())

    started = client.post("/chat", json={"message": "book appointment"})
    sid = started.json()["session_id"]
    confirmed = client.post("/chat", json={"message": "confirm appointment", "session_id": sid})
    assert confirmed.status_code == 200

    after = client.get("/admin/appointments?limit=200", headers=ADMIN)
    assert after.status_code == 200
    after_items = after.json()
    assert len(after_items) >= before_count + 1
