"""POST /ratios and DELETE /ratios/{id}.

add_ratio auto-tracks both tickers (idempotent) so the ratio is guaranteed
queryable as soon as the request returns. The same Polygon-backfill TODO from
tickers.py applies if latency becomes an issue.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from equity_rotation_shared.models import ratios as ratios_tbl
from equity_rotation_shared.polygon import ensure_ticker_tracked

from ..deps import db_engine
from ..schemas import AddRatioRequest, RatioResponse

router = APIRouter(prefix="/ratios", tags=["ratios"])


@router.post("", response_model=RatioResponse, status_code=status.HTTP_201_CREATED)
def add_ratio(
    payload: AddRatioRequest, engine: Engine = Depends(db_engine)
) -> RatioResponse:
    if payload.numerator == payload.denominator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="numerator and denominator must differ",
        )

    # Ensure both tickers are tracked + backfilled. Idempotent for tickers that
    # already exist and are current.
    try:
        ensure_ticker_tracked(engine, payload.numerator)
        ensure_ticker_tracked(engine, payload.denominator)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backfill failed while adding ratio: {exc}",
        ) from exc

    stmt = (
        ratios_tbl.insert()
        .values(
            numerator=payload.numerator,
            denominator=payload.denominator,
            group_name=payload.group_name,
        )
        .returning(
            ratios_tbl.c.id,
            ratios_tbl.c.numerator,
            ratios_tbl.c.denominator,
            ratios_tbl.c.group_name,
            ratios_tbl.c.created_at,
        )
    )

    try:
        with engine.begin() as conn:
            row = conn.execute(stmt).one()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ratio already exists for this (numerator, denominator, group)",
        ) from exc

    return RatioResponse(
        id=row.id,
        numerator=row.numerator,
        denominator=row.denominator,
        group_name=row.group_name,
        created_at=row.created_at,
    )


@router.delete("/{ratio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ratio(ratio_id: int, engine: Engine = Depends(db_engine)) -> None:
    with engine.begin() as conn:
        result = conn.execute(delete(ratios_tbl).where(ratios_tbl.c.id == ratio_id))
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown ratio id {ratio_id}"
        )
