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

## Tests
- Run: `pytest`

## Important
This bot provides informational assistance and does not replace professional medical diagnosis.
