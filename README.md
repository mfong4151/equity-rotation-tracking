# equity-rotation-tracking

Local dev quickstart for the API (FastAPI) and frontend (Vite + React).

For Raspberry Pi / systemd deployment, see [api/README.md](api/README.md).

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A running Postgres with `DATABASE_URL` set in `api/.env` (see `api/.env.example`)

## Backend (FastAPI on :8000)

One-time setup:

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../shared
```

Run the dev server (auto-reload):

```bash
cd api
source .venv/bin/activate
set -a; source .env; set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API is now at <http://localhost:8000> (docs at `/docs`).

## Frontend (Vite on :5173)

One-time setup:

```bash
cd frontend
npm install
```

Run the dev server (auto-reload / HMR):

```bash
cd frontend
npm run dev
```

Frontend is now at <http://localhost:5173>. It expects the API at
<http://localhost:8000> (override via `VITE_API_BASE_URL` in `frontend/.env`).

## Offline jobs (optional, manual run)

```bash
cd offline-jobs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../shared

# nightly data pull
python -m data_collector_job
# prune old rows
python -m data_cleanup_job
```
