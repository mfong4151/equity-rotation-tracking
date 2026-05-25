"""FastAPI entrypoint.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from .routers import groups, ratios, tickers

app = FastAPI(title="equity-rotation-tracking API", version="0.1.0")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tickers.router)
app.include_router(ratios.router)
app.include_router(groups.router)
