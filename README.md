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

## Admin performance
- Admin list endpoints use short-lived caching for faster repeated reads.
- Cache is automatically invalidated after lead/appointment write operations.

## API endpoints
- `GET /health`
- `POST /chat`
- `POST /reset`
- `GET /admin/leads` (requires `x-admin-token`)
- `GET /admin/appointments` (requires `x-admin-token`)
- `GET /admin/stats` (requires `x-admin-token`) — uses efficient `COUNT(*)` queries
- `GET /admin/stats/breakdown` (requires `x-admin-token`) — grouped counts by lead intent and appointment status
- `GET /admin/leads/export` (requires `x-admin-token`) — download leads as CSV
- `GET /admin/appointments/export` (requires `x-admin-token`) — download appointments as CSV
- `GET /admin/sessions/active` (requires `x-admin-token`)
- `POST /admin/sessions/cleanup?dry_run=true` (requires `x-admin-token`)

### CSV exports

Both export endpoints return a `text/csv` file with a timestamped filename.

```sh
# Download all leads
curl -H "x-admin-token: change-me" http://localhost:8000/admin/leads/export -o leads.csv

# Download all appointments
curl -H "x-admin-token: change-me" http://localhost:8000/admin/appointments/export -o appointments.csv
```

### Query validation

Admin list/search/export endpoints enforce validation for pagination and limits:
- `limit >= 1`
- `offset >= 0` (where applicable)
- `limit <= 10000`

Invalid values return HTTP `422`.

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
