"""Simple smoke checks for the Dentist Assistant API."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.api import app


def main() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, f"health failed: {health.status_code}"
    assert health.json()["status"] == "ok"

    chat = client.post("/chat", json={"message": "what are your hours?"})
    assert chat.status_code == 200, f"chat failed: {chat.status_code}"
    payload = chat.json()
    assert "reply" in payload and payload["reply"], "missing reply"
    assert "session_id" in payload and payload["session_id"], "missing session_id"

    print("Smoke test passed ✅")


if __name__ == "__main__":
    main()
