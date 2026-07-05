# equity-rotation-tracking

Local dev quickstart for the API (FastAPI) and frontend (Vite + React).

For Raspberry Pi / systemd deployment, see [api/README.md](api/README.md).

## Roadmap / TODO

- **Mobile / off-network access.** The current Pi deployment is local/LAN only
  (reachable at `http://<pi-ip>:8000`). On-LAN phones already work; supporting
  phones off the home network is future work — likely **Tailscale** (private, no
  domain/open ports) or a Cloudflare Tunnel + Access for a public URL. Tracked
  in [#2](https://github.com/mfong4151/equity-rotation-tracking/issues/2).

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

## Offline jobs (scheduled via cron)

`data_collector_job` (nightly Polygon pull) and `data_cleanup_job` (prune old
rows) are intended to be run automatically on a schedule via cron, not by
hand. `offline-jobs/run_daily.sh` is the entrypoint: it activates the venv,
runs the collector, then the cleanup, and writes logs to
`offline-jobs/logs/`.

One-time setup:

```bash
cd offline-jobs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../shared
cp .env.example .env   # set POLYGON_API_KEY + DATABASE_URL
```

Smoke test (runs both jobs once):

```bash
./run_daily.sh
tail logs/run_daily.log logs/collector.log logs/cleanup.log
```

Schedule it — `crontab -e` and append (Mon–Fri at 18:30 local, post-close):

```cron
MAILTO=""
30 18 * * 1-5 /home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/offline-jobs/run_daily.sh
```

Verify:

```bash
crontab -l
tail -f offline-jobs/logs/run_daily.log
```

The Pi deployment guide ([api/README.md](api/README.md)) covers the same
flow with paths assumed to live under the repo checkout.

---

## Production deployment (Pi + Cloudflare)

Goal: jobs + Postgres + API on a Raspberry Pi at home, frontend reachable
from any browser on the internet. Recommended stack:

- **Pi**: offline jobs, Postgres, FastAPI API (already covered in
  [api/README.md](api/README.md)).
- **Cloudflare Tunnel** (`cloudflared`): exposes the Pi's API as
  `https://api.yourdomain.com` with no port-forwarding and no public IP.
- **Cloudflare Pages**: hosts the static frontend at
  `https://app.yourdomain.com`.
- **Cloudflare Access**: gates the API behind email login (the API is
  unauthenticated today; do not skip this).

Prereqs: a domain on Cloudflare (~$10/yr). Alternatives if you don't want
Cloudflare: Tailscale (private — only your devices can reach it), or
port-forward + DuckDNS + Caddy/Let's Encrypt (fully self-hosted, you manage
TLS and an open port).

### 1. Deploy backend on the Pi

Follow [api/README.md](api/README.md) for Postgres, schema, offline-jobs cron,
and the `equity-rotation-api` systemd service. End state: API responds locally
at `http://<pi-ip>:8000/health`.

### 2. Expose the API with Cloudflare Tunnel

On the Pi:

```bash
# Install cloudflared (arm64)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb \
  -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb

# Authenticate (opens a URL — log into Cloudflare in a browser)
cloudflared tunnel login

# Create the tunnel
cloudflared tunnel create equity-rotation

# Route a hostname (creates the DNS record for you)
cloudflared tunnel route dns equity-rotation api.yourdomain.com
```

Create `/etc/cloudflared/config.yml`:

```yaml
tunnel: equity-rotation
credentials-file: /home/mfong415/.cloudflared/<tunnel-uuid>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

Install as a service:

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

Verify from anywhere: `curl https://api.yourdomain.com/health` → `{"status":"ok"}`.

### 3. Lock down the API with Cloudflare Access

In the Cloudflare dashboard:

1. **Zero Trust** → **Access** → **Applications** → **Add an application** →
   **Self-hosted**.
2. Application domain: `api.yourdomain.com`.
3. Add a policy: action **Allow**, include **Emails** → your email
   address(es). Save.

The API is now behind an email/one-time-PIN gate. The frontend will also
need to authenticate (see step 5).

### 4. Configure CORS on the API

Edit `api/.env` on the Pi to include the frontend origin:

```bash
CORS_ORIGINS=https://app.yourdomain.com,http://localhost:5173
```

Then restart:

```bash
sudo systemctl restart equity-rotation-api
```

### 5. Deploy the frontend on Cloudflare Pages

Locally, set the production API URL:

```bash
# frontend/.env.production
VITE_API_BASE_URL=https://api.yourdomain.com
```

Then in the Cloudflare dashboard:

1. **Workers & Pages** → **Create** → **Pages** → **Connect to Git** →
   pick the repo.
2. Build settings:
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Environment variable: `VITE_API_BASE_URL=https://api.yourdomain.com`
   (Production).
4. After the first deploy, **Custom domains** → add `app.yourdomain.com`.
5. Apply the **same** Cloudflare Access policy to `app.yourdomain.com` (or
   make the API call carry the Access JWT — easiest is to gate both
   hostnames the same way so a single login covers both).

### 6. Verify end-to-end

- `https://app.yourdomain.com` loads, prompts for Access login.
- Sidebar populates groups → calls to `https://api.yourdomain.com/groups`
  succeed in DevTools.
- Adding a ratio works; the next cron run on the Pi backfills data.

### Updating

- **Backend**: `git pull` on the Pi, then
  `sudo systemctl restart equity-rotation-api` (re-run `pip install -r` if
  requirements changed, re-apply `schema.sql` if it changed).
- **Frontend**: push to the tracked branch; Cloudflare Pages rebuilds and
  redeploys automatically.
