"""Environment variable helpers.

`load_env()` is idempotent — calling it multiple times has no effect after the
first. It searches upward from the caller's CWD for a `.env` file.
"""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv

_loaded = False


def load_env() -> None:
    global _loaded
    if _loaded:
        return
    # Walk up from the process CWD so api/ or offline-jobs/ .env files are found
    # regardless of where the importing module lives.
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path)
    _loaded = True


def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val
