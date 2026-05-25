"""GET /groups/{group_name} — fetch all ratios in a group with their time series.

For each ratio tagged with the given group, joins stock_data on both legs by
date and returns the resulting ratio series. Computed on read; no precomputed
metrics yet.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Engine, and_, select

from equity_rotation_shared.models import ratios as ratios_tbl, stock_data

from ..deps import db_engine
from ..schemas import GroupResponse, RatioPoint, RatioSeries

router = APIRouter(prefix="/groups", tags=["groups"])

# Two aliases of stock_data so the numerator and denominator legs of every
# ratio can be joined in a single query.
_num_bars = stock_data.alias("n")
_den_bars = stock_data.alias("d")

_TIMEFRAME = "1d"


@router.get("/{group_name}", response_model=GroupResponse)
def batch_get_group(
    group_name: str,
    days: int = Query(default=120, ge=1, le=365),
    engine: Engine = Depends(db_engine),
) -> GroupResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            ratios_tbl.c.id.label("ratio_id"),
            ratios_tbl.c.numerator,
            ratios_tbl.c.denominator,
            _num_bars.c.price_timestamp.label("bar_ts"),
            _num_bars.c.close.label("num_close"),
            _den_bars.c.close.label("den_close"),
        )
        .select_from(
            ratios_tbl.join(
                _num_bars,
                and_(
                    _num_bars.c.ticker_symbol == ratios_tbl.c.numerator,
                    _num_bars.c.timeframe == _TIMEFRAME,
                ),
            ).join(
                _den_bars,
                and_(
                    _den_bars.c.ticker_symbol == ratios_tbl.c.denominator,
                    _den_bars.c.timeframe == _TIMEFRAME,
                    _den_bars.c.price_timestamp == _num_bars.c.price_timestamp,
                ),
            )
        )
        .where(
            ratios_tbl.c.group_name == group_name,
            _num_bars.c.price_timestamp >= cutoff,
        )
        .order_by(ratios_tbl.c.id, _num_bars.c.price_timestamp)
    )

    with engine.connect() as conn:
        rows = conn.execute(stmt).all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ratios in group '{group_name}' (or no overlapping bars in window)",
        )

    by_ratio: dict[int, dict] = {}
    points_by_ratio: dict[int, list[RatioPoint]] = defaultdict(list)

    for row in rows:
        rid = row.ratio_id
        by_ratio.setdefault(
            rid,
            {"id": rid, "numerator": row.numerator, "denominator": row.denominator},
        )
        den = float(row.den_close)
        if den == 0:
            continue
        points_by_ratio[rid].append(
            RatioPoint(
                date=row.bar_ts.date().isoformat(),
                numerator_close=float(row.num_close),
                denominator_close=den,
                ratio=float(row.num_close) / den,
            )
        )

    series = [
        RatioSeries(**meta, points=points_by_ratio[rid])
        for rid, meta in by_ratio.items()
    ]
    return GroupResponse(group=group_name, days=days, ratios=series)
