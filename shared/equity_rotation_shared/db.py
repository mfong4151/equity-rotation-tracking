"""SQLAlchemy Engine factory.

DATABASE_URL must use the `postgresql+psycopg://` scheme (SQLAlchemy + psycopg3).
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from .env import load_env, require_env


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy Engine.

    Pool defaults are fine for this scale (single-user dashboard + nightly job).
    """
    load_env()
    url = require_env("DATABASE_URL")
    return create_engine(url, pool_pre_ping=True, future=True)
