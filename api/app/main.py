"""FastAPI entrypoint.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import groups, ratios, tickers

app = FastAPI(title="equity-rotation-tracking API", version="0.1.0")

# Comma-separated list of allowed origins; defaults cover the Vite dev server.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tickers.router)
app.include_router(ratios.router)
app.include_router(groups.router)
