"""FastAPI dependency wiring.

Exposes a `db_engine` dependency so routes can pull the shared engine without
importing the singleton directly (easier to swap in tests).
"""

from __future__ import annotations

from sqlalchemy import Engine

from equity_rotation_shared import get_engine


def db_engine() -> Engine:
    return get_engine()
