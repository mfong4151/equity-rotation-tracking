"""Polygon ingestion helpers.

Single source of truth for "fetch daily OHLC from Polygon and upsert into
stock_data". Used by:
  * offline-jobs/data_collector_job  — bulk daily run
  * api/app/routers/tickers          — synchronous backfill on add_ticker
  * api/app/routers/ratios           — auto-backfill when add_ratio sees a
                                       ticker with no data yet
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import requests
from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func

from .env import require_env
from .models import stock_data, tickers

POLYGON_AGGS_URL = (
    "https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{from_}/{to}"
)
DEFAULT_TIMEFRAME = "1d"


def default_backfill_days() -> int:
    return int(os.getenv("COLLECTOR_INITIAL_BACKFILL_DAYS", "400"))


def fetch_polygon_daily(
    ticker: str, from_: date, to: date, api_key: str | None = None
) -> list[dict]:
    """Return Polygon aggregate results for an inclusive date range.

    Each result is a dict with keys t/o/h/l/c (ms epoch + OHLC).
    """
    if api_key is None:
        api_key = require_env("POLYGON_API_KEY")

    url = POLYGON_AGGS_URL.format(
        ticker=ticker, from_=from_.isoformat(), to=to.isoformat()
    )
    resp = requests.get(
        url,
        params={"adjusted": "true", "sort": "asc", "apiKey": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") == "ERROR":
        raise RuntimeError(f"Polygon error for {ticker}: {payload}")
    return payload.get("results") or []


def latest_bar_date(
    engine: Engine, ticker: str, timeframe: str = DEFAULT_TIMEFRAME
) -> date | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(stock_data.c.price_timestamp)
            .where(
                stock_data.c.ticker_symbol == ticker,
                stock_data.c.timeframe == timeframe,
            )
            .order_by(stock_data.c.price_timestamp.desc())
            .limit(1)
        ).first()
    return row[0].date() if row else None


def upsert_bars(
    engine: Engine, ticker: str, timeframe: str, results: list[dict]
) -> int:
    if not results:
        return 0
    rows = [
        {
            "ticker_symbol": ticker,
            "timeframe": timeframe,
            "price_timestamp": datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc),
            "open": r["o"],
            "high": r["h"],
            "low": r["l"],
            "close": r["c"],
        }
        for r in results
    ]
    stmt = pg_insert(stock_data).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker_symbol", "timeframe", "price_timestamp"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    return len(rows)


def mark_ticker_ingested(engine: Engine, ticker: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            tickers.update()
            .where(tickers.c.ticker_symbol == ticker)
            .values(last_ingest_at=func.now())
        )


def ensure_ticker_tracked(
    engine: Engine,
    ticker: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    backfill_days: int | None = None,
    api_key: str | None = None,
) -> dict:
    """Idempotent: ensure `ticker` is in the tickers table, and that stock_data
    has bars for it. Backfills from Polygon if missing.

    Returns a small summary dict: {ticker, inserted, bars_added, latest_bar}.
    """
    if backfill_days is None:
        backfill_days = default_backfill_days()

    inserted = False
    with engine.begin() as conn:
        ins = (
            pg_insert(tickers)
            .values(ticker_symbol=ticker)
            .on_conflict_do_nothing(index_elements=["ticker_symbol"])
        )
        result = conn.execute(ins)
        inserted = result.rowcount > 0

    latest = latest_bar_date(engine, ticker, timeframe)
    today = date.today()
    target_to = today - timedelta(days=1)
    if latest is None:
        from_ = target_to - timedelta(days=backfill_days)
    else:
        from_ = latest + timedelta(days=1)

    bars_added = 0
    if from_ <= target_to:
        results = fetch_polygon_daily(ticker, from_, target_to, api_key=api_key)
        bars_added = upsert_bars(engine, ticker, timeframe, results)
        mark_ticker_ingested(engine, ticker)
        latest = latest_bar_date(engine, ticker, timeframe)

    return {
        "ticker": ticker,
        "ticker_inserted": inserted,
        "bars_added": bars_added,
        "latest_bar": latest.isoformat() if latest else None,
    }
