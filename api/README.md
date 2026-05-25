# Deploying equity-rotation-tracking on a Raspberry Pi

This guide covers deploying the full backend on a Raspberry Pi (tested on Pi 4/5
running Raspberry Pi OS Bookworm, 64-bit):

1. **Offline jobs** — `data_collector_job` and `data_cleanup_job`, run nightly by cron.
2. **API** — the FastAPI service, run under systemd.

Both share the same Postgres database and the same `equity_rotation_shared`
package.

---

## 1. Prerequisites (run once)

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql git
```

Confirm Postgres is up:

```bash
sudo systemctl status postgresql
```

Create the role + database (replace user/password to match your `.env`):

```bash
sudo -u postgres psql <<'SQL'
CREATE USER mfong415 WITH PASSWORD 'dev123';
CREATE DATABASE equity_rotation OWNER mfong415;
SQL
```

Clone the repo to a stable location, e.g.:

```bash
git clone https://github.com/mfong4151/equity-rotation-tracking.git \
  ~/projects/equity-analysis-tools/equity-rotation-tracking
cd ~/projects/equity-analysis-tools/equity-rotation-tracking
```

Apply the schema (one time, seeds SPY/QQQ/IWM):

```bash
psql "postgresql://mfong415:dev123@localhost/equity_rotation" -f api/sql/schema.sql
```

---

## 2. Deploy the offline jobs

```bash
cd offline-jobs

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# Edit .env: set POLYGON_API_KEY and confirm DATABASE_URL
nano .env
```

Smoke test (skip cron):

```bash
./run_daily.sh
tail logs/run_daily.log logs/collector.log logs/cleanup.log
```

Schedule via cron — `crontab -e` and append:

```
# Equity rotation: Mon–Fri at 18:30 local (post-close + buffer)
MAILTO=""
30 18 * * 1-5 /home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/offline-jobs/run_daily.sh
```

Verify:

```bash
crontab -l
journalctl -u cron --since today
```

---

## 3. Deploy the API

```bash
cd ../api

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
nano .env  # same DATABASE_URL as offline-jobs; POLYGON_API_KEY required for backfill on add
```

Smoke test:

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# In another shell:
curl http://<pi-ip>:8000/health
```

Run it under systemd so it survives reboots. Create
`/etc/systemd/system/equity-rotation-api.service`:

```ini
[Unit]
Description=Equity rotation tracking API
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=mfong415
WorkingDirectory=/home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/api
EnvironmentFile=/home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/api/.env
ExecStart=/home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now equity-rotation-api
sudo systemctl status equity-rotation-api
journalctl -u equity-rotation-api -f
```

The API is now reachable at `http://<pi-ip>:8000`. Swagger UI lives at `/docs`.

---

## 4. Updating

```bash
cd ~/projects/equity-analysis-tools/equity-rotation-tracking
git pull

# If shared/ changed, both venvs pick it up automatically (installed with -e).
# If requirements changed:
api/.venv/bin/pip install -r api/requirements.txt
offline-jobs/.venv/bin/pip install -r offline-jobs/requirements.txt

# If schema.sql changed:
psql "postgresql://mfong415:dev123@localhost/equity_rotation" -f api/sql/schema.sql

sudo systemctl restart equity-rotation-api
```

---

## API endpoints (reference)

| Method | Path                  | Description                                          |
| ------ | --------------------- | ---------------------------------------------------- |
| POST   | `/tickers`            | Add a ticker; backfills OHLC from Polygon.           |
| DELETE | `/tickers/{symbol}`   | Remove a ticker (cascades to stock_data + ratios).   |
| POST   | `/ratios`             | Add a ratio; auto-backfills both legs if needed.     |
| DELETE | `/ratios/{id}`        | Remove a ratio. No cascade.                          |
| GET    | `/groups/{name}?days` | All ratios in a group + their time series (default `days=120`, max 365). |
| GET    | `/health`             | Liveness check.                                      |
