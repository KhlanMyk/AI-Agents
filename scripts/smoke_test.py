"""Simple smoke checks for the Dentist Assistant API."""

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.api import app


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run API smoke checks")
    parser.add_argument(
        "--check-admin",
        action="store_true",
        help="Also verify admin endpoint access with x-admin-token.",
    )
    parser.add_argument(
        "--admin-token",
        default=os.getenv("ADMIN_TOKEN", "change-me"),
        help="Admin token used when --check-admin is enabled.",
    )
    return parser


def main(check_admin: bool = False, admin_token: str = "change-me") -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, f"health failed: {health.status_code}"
    assert health.json()["status"] == "ok"
    assert "X-Request-ID" in health.headers, "missing request tracing header"

    chat = client.post("/chat", json={"message": "what are your hours?"})
    assert chat.status_code == 200, f"chat failed: {chat.status_code}"
    payload = chat.json()
    assert "reply" in payload and payload["reply"], "missing reply"
    assert "session_id" in payload and payload["session_id"], "missing session_id"

    if check_admin:
        admin = client.get("/admin/stats", headers={"x-admin-token": admin_token})
        assert admin.status_code == 200, f"admin stats failed: {admin.status_code}"
        body = admin.json()
        assert "total_leads" in body, "missing total_leads"
        assert "total_appointments" in body, "missing total_appointments"

    print("Smoke test passed ✅")


if __name__ == "__main__":
    args = _build_parser().parse_args()
    main(check_admin=args.check_admin, admin_token=args.admin_token)
