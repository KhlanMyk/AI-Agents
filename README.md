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
- `GET /admin/leads/trends` (requires `x-admin-token`) — daily lead volume trend for last N days
- `GET /admin/appointments/trends` (requires `x-admin-token`) — daily appointment trend for last N days
- `GET /admin/rate-limit/{session_id}` (requires `x-admin-token`) — inspect current limiter usage for a session
- `POST /admin/rate-limit/reset` (requires `x-admin-token`) — reset one session or all limiter counters
- `POST /admin/data/cleanup` (requires `x-admin-token`) — dry-run or execute retention cleanup for old DB records
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

### Trends endpoints

Both trends endpoints accept `days` in range `1..90` (default `7`) and return a date/count series.

```sh
# Leads trend for last 14 days
curl -H "x-admin-token: change-me" "http://localhost:8000/admin/leads/trends?days=14"

# Appointments trend for last 30 days
curl -H "x-admin-token: change-me" "http://localhost:8000/admin/appointments/trends?days=30"
```

### Rate-limit admin controls

```sh
# Inspect limiter usage for one session
curl -H "x-admin-token: change-me" http://localhost:8000/admin/rate-limit/<session_id>

# Reset limiter counters for a single session
curl -X POST -H "x-admin-token: change-me" -H "content-type: application/json" \
   http://localhost:8000/admin/rate-limit/reset \
   -d '{"session_id": "<session_id>"}'

# Reset limiter counters for all tracked sessions
curl -X POST -H "x-admin-token: change-me" -H "content-type: application/json" \
   http://localhost:8000/admin/rate-limit/reset \
   -d '{}'
```

### Data retention cleanup

Cleanup endpoint supports dry-run by default and accepts `days` in `1..3650`.

```sh
# Preview records older than 365 days (no deletion)
curl -X POST -H "x-admin-token: change-me" \
   "http://localhost:8000/admin/data/cleanup?days=365&dry_run=true"

# Execute deletion for records older than 365 days
curl -X POST -H "x-admin-token: change-me" \
   "http://localhost:8000/admin/data/cleanup?days=365&dry_run=false"
```

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
