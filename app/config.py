from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'dentist_app.db'}")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")

# Comma-separated list of allowed CORS origins.
# Override via env var CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
_raw_origins = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS: list[str] = [
    o.strip() for o in _raw_origins.split(",") if o.strip()
]
