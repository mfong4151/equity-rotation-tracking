# offline-jobs

Two scheduled scripts that keep `stock_data` fresh and bounded:

| Job                  | What it does                                                 |
| -------------------- | ------------------------------------------------------------ |
| `data_collector_job` | For every active row in `tickers`, backfill missing daily bars from Polygon into `stock_data`. |
| `data_cleanup_job`   | Delete `stock_data` rows older than `CLEANUP_RETENTION_DAYS` (default 365). |

Driven by OS `cron` via [run_daily.sh](run_daily.sh). Collector runs first; on success, cleanup runs.

## One-time setup

```bash
cd offline-jobs

# 1. venv + deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. env
cp .env.example .env
$EDITOR .env   # set POLYGON_API_KEY, DATABASE_URL

# 3. database
createdb equity_rotation   # or whatever you named it in DATABASE_URL
psql "postgresql://${USER}@localhost/equity_rotation" -f ../api/sql/schema.sql
# (schema.sql seeds SPY/QQQ/IWM; no manual ticker insert needed.)
```

## Smoke test (no cron)

```bash
./run_daily.sh
tail logs/run_daily.log logs/collector.log logs/cleanup.log
```

## Schedule it

```bash
crontab -e
```

Append:

```
# Equity rotation: Mon–Fri at 18:30 local (~post-close + buffer)
MAILTO=mfong415
30 18 * * 1-5 /home/mfong415/projects/equity-analysis-tools/equity-rotation-tracking/offline-jobs/run_daily.sh
```

Verify:

```bash
crontab -l
grep CRON /var/log/syslog | tail   # or: journalctl -u cron --since today
```

## Adding / removing tickers

The collector reads from the `tickers` table — there's no list to edit here.

```sql
-- Add
INSERT INTO tickers (ticker_symbol) VALUES ('XLF');

-- Pause (collector ignores, cleanup leaves existing rows alone until retention expires)
UPDATE tickers SET is_active = FALSE WHERE ticker_symbol = 'XLF';

-- Hard delete (also deletes all stock_data rows for that ticker, via ON DELETE CASCADE)
DELETE FROM tickers WHERE ticker_symbol = 'XLF';
```

The API (TBD) will expose these as endpoints; the frontend's add-ticker UI calls them.

## Files

```
offline-jobs/
  .env.example          template env file
  .gitignore
  requirements.txt
  common.py             shared DB / env helpers
  run_daily.sh          cron entrypoint: collector then cleanup
  data_collector_job/
    __init__.py
    __main__.py         entrypoint: `python -m data_collector_job`
  data_cleanup_job/
    __init__.py
    __main__.py
  logs/                 (gitignored) created on first run
```
