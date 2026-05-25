# api

FastAPI service for managing tickers + ratios and computing on-read ratio time series.

## Endpoints

| Method | Path                  | Description                                          |
| ------ | --------------------- | ---------------------------------------------------- |
| POST   | `/tickers`            | Add a ticker; backfills OHLC from Polygon.           |
| DELETE | `/tickers/{symbol}`   | Remove a ticker (cascades to stock_data + ratios).   |
| POST   | `/ratios`             | Add a ratio; auto-backfills both legs if needed.     |
| DELETE | `/ratios/{id}`        | Remove a ratio. No cascade.                          |
| GET    | `/groups/{name}?days` | All ratios in a group + their time series (default `days=120`, max 365). |
| GET    | `/health`             | Liveness check.                                      |

## Setup

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
$EDITOR .env

# DB schema (one-time):
psql "$(grep '^DATABASE_URL=' .env | cut -d= -f2- | sed 's|postgresql+psycopg|postgresql|')" -f sql/schema.sql
```

## Run

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> for Swagger UI.

## Quick smoke test

```bash
# add a ticker (backfills ~400d)
curl -X POST http://localhost:8000/tickers \
  -H 'Content-Type: application/json' \
  -d '{"ticker_symbol":"NVDA"}'

# add a ratio (auto-backfills both legs if needed)
curl -X POST http://localhost:8000/ratios \
  -H 'Content-Type: application/json' \
  -d '{"numerator":"NVDA","denominator":"SOXX","group_name":"Semiconductors"}'

# fetch the group
curl 'http://localhost:8000/groups/Semiconductors?days=90'

# delete
curl -X DELETE http://localhost:8000/ratios/1
curl -X DELETE http://localhost:8000/tickers/NVDA
```

## Layout

```
api/
  sql/schema.sql           source of truth for the DB schema
  requirements.txt         fastapi, uvicorn, -e ../shared
  app/
    main.py                FastAPI app + router includes
    deps.py                db_engine dependency
    schemas.py             pydantic request/response models
    routers/
      tickers.py
      ratios.py
      groups.py
```
