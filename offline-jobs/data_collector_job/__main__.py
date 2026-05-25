"""Daily Polygon OHLC collector.

Iterates active tickers and delegates to shared.ensure_ticker_tracked, which
handles "find latest stored bar -> backfill missing -> upsert -> mark ingested".

Throws if there are no active tickers (the table should never be empty in
practice; schema.sql seeds SPY/QQQ/IWM).
"""

from __future__ import annotations

import os
import time

from sqlalchemy import select

from equity_rotation_shared import get_engine, load_env
from equity_rotation_shared.models import tickers
from equity_rotation_shared.polygon import (
    DEFAULT_TIMEFRAME,
    ensure_ticker_tracked,
)

REQUEST_SLEEP_SECONDS = 12  # Polygon free tier: ~5 req/min.


def main() -> int:
    """Backfill daily OHLC bars for every active ticker.

    Loads env, reads the active rows from the tickers table, and calls
    ensure_ticker_tracked on each — which fetches any missing bars from
    Polygon and upserts them into stock_data. Sleeps REQUEST_SLEEP_SECONDS
    between tickers to stay under the Polygon free-tier rate limit.
    Raises RuntimeError if no active tickers exist.
    """
    load_env()
    timeframe = os.getenv("COLLECTOR_TIMEFRAME", DEFAULT_TIMEFRAME)
    engine = get_engine()

    active = fetch_active_tickers(engine)
    if not active:
        raise RuntimeError(
            "collector: no active tickers — refusing to run. "
            "Re-apply schema.sql or INSERT a row into tickers."
        )
    print(f"collector: {len(active)} active tickers", flush=True)

    for i, ticker in enumerate(active):
        try:
            summary = ensure_ticker_tracked(engine, ticker, timeframe=timeframe)
            print(
                f"  [{i + 1}/{len(active)}] {ticker}: "
                f"+{summary['bars_added']} bars, latest={summary['latest_bar']}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i + 1}/{len(active)}] {ticker}: FAILED {exc}", flush=True)

        time.sleep(REQUEST_SLEEP_SECONDS)

    return 0


def fetch_active_tickers(engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(tickers.c.ticker_symbol)
            .where(tickers.c.is_active.is_(True))
            .order_by(tickers.c.ticker_symbol)
        ).all()
    return [r[0] for r in rows]


if __name__ == "__main__":
    raise SystemExit(main())
