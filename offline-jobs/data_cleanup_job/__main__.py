"""Rolling-window cleanup of stock_data.

Deletes any bars older than CLEANUP_RETENTION_DAYS (default 365). Run right
after the collector so the DB never holds more than ~1 year per ticker.
"""

from __future__ import annotations

import os

from sqlalchemy import delete, text

from equity_rotation_shared import get_engine, load_env
from equity_rotation_shared.models import stock_data


def main() -> int:
    """Delete stock_data bars older than CLEANUP_RETENTION_DAYS.

    Reads the retention window from the env (default 365 days), deletes every
    row in stock_data with a price_timestamp older than that cutoff, and prints
    a one-line summary. Run nightly after the collector so the table stays
    bounded to roughly one rolling year per ticker.
    """
    load_env()
    retention_days = int(os.getenv("CLEANUP_RETENTION_DAYS", "365"))
    engine = get_engine()

    cutoff_expr = text("NOW() - make_interval(days => :days)").bindparams(
        days=retention_days
    )

    with engine.begin() as conn:
        result = conn.execute(
            delete(stock_data).where(stock_data.c.price_timestamp < cutoff_expr)
        )
        deleted = result.rowcount

    print(
        f"cleanup: deleted {deleted} rows older than {retention_days} days",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
