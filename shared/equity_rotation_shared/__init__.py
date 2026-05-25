"""Shared building blocks for the equity-rotation-tracking project.

Both the offline jobs and the FastAPI service depend on this package via
`pip install -e ../shared`. It defines:
  * SQLAlchemy Core Table objects mirroring api/sql/schema.sql
  * an Engine factory that reads DATABASE_URL
  * a Polygon backfill function used by the collector and add_ticker/add_ratio
  * env-loading helpers
"""

from .env import load_env, require_env
from .db import get_engine
from . import models, polygon

__all__ = ["load_env", "require_env", "get_engine", "models", "polygon"]
