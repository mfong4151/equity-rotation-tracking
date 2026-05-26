"""POST /tickers and DELETE /tickers/{symbol}.

TODO: add_ticker currently backfills synchronously. If the Polygon round-trip
plus DB upsert blows past ~2s and impacts the UI, refactor to fire-and-forget:
queue a job (e.g. add a row to a `backfill_jobs` table polled by a worker, or
use a FastAPI BackgroundTask if a single in-process worker is acceptable).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Engine, delete

from equity_rotation_shared.models import tickers as tickers_tbl
from equity_rotation_shared.polygon import ensure_ticker_tracked

from ..deps import db_engine
from ..schemas import (
    AddTickerRequest,
    BatchAddTickerRequest,
    BatchAddTickerResponse,
    BatchTickerResult,
    TickerResponse,
)

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.post("", response_model=TickerResponse, status_code=status.HTTP_201_CREATED)
def add_ticker(
    payload: AddTickerRequest, engine: Engine = Depends(db_engine)
) -> TickerResponse:
    try:
        summary = ensure_ticker_tracked(engine, payload.ticker_symbol)
    except Exception as exc:  # noqa: BLE001 — surface upstream errors as 502
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backfill failed for {payload.ticker_symbol}: {exc}",
        ) from exc

    return TickerResponse(
        ticker_symbol=summary["ticker"],
        bars_added=summary["bars_added"],
        latest_bar=summary["latest_bar"],
    )


@router.post("/batch", response_model=BatchAddTickerResponse)
def add_tickers_batch(
    payload: BatchAddTickerRequest, engine: Engine = Depends(db_engine)
) -> BatchAddTickerResponse:
    results: list[BatchTickerResult] = []
    for symbol in payload.ticker_symbols:
        try:
            summary = ensure_ticker_tracked(engine, symbol)
            results.append(
                BatchTickerResult(
                    ticker_symbol=summary["ticker"],
                    ok=True,
                    bars_added=summary["bars_added"],
                    latest_bar=summary["latest_bar"],
                )
            )
        except Exception as exc:  # noqa: BLE001 — collected per-symbol
            results.append(
                BatchTickerResult(ticker_symbol=symbol, ok=False, error=str(exc))
            )
    return BatchAddTickerResponse(results=results)


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticker(symbol: str, engine: Engine = Depends(db_engine)) -> None:
    symbol = symbol.strip().upper()
    with engine.begin() as conn:
        result = conn.execute(
            delete(tickers_tbl).where(tickers_tbl.c.ticker_symbol == symbol)
        )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown ticker {symbol}"
        )
