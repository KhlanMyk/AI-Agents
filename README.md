# Dentist Assistant App

Production-ready starter for a dental clinic assistant:
- terminal chatbot (`dentist_agent.py`)
- web chat UI (`/`)
- REST API (`/chat`, `/reset`, `/admin/*`)
- SQLite persistence for leads and appointments

## Quick start
1. Install dependencies:
   - `pip install -r requirements.txt`
2. Start server:
   - `python run.py`
3. Open:
   - `http://127.0.0.1:8000`

## CLI assistant
- Interactive mode:
   - `python dentist_agent.py`
- One-shot mode:
   - `python dentist_agent.py --message "what are your hours?"`
- Disable colors:
   - `python dentist_agent.py --no-color`
- Export transcript to JSON:
   - `python dentist_agent.py --export data/cli_transcript.json`
- Export transcript with auto-generated timestamped filename:
   - `python dentist_agent.py --export-dir data/exports`

## Docker
- Build and run with Docker Compose:
  - `docker compose up --build`
- Open:
  - `http://127.0.0.1:8000`

The compose setup mounts `./data` into the container so SQLite data persists locally.

## API endpoints
- `GET /health`
- `POST /chat`
- `POST /reset`
- `GET /admin/leads` (requires `x-admin-token`)
- `GET /admin/appointments` (requires `x-admin-token`)
- `GET /admin/stats` (requires `x-admin-token`)

## Environment
Use `.env`:
- `DATABASE_URL=sqlite:///data/dentist_app.db`
- `ADMIN_TOKEN=change-me`
- `CORS_ORIGINS=*`

Optional runtime variables:
- `HOST=0.0.0.0`
- `PORT=8000`
- `RELOAD=false`

## Tests
- Run: `pytest`

## Smoke test
- Quick API check:
  - `python scripts/smoke_test.py`
- Include admin verification:
  - `python scripts/smoke_test.py --check-admin`

## Important
This bot provides informational assistance and does not replace professional medical diagnosis.
