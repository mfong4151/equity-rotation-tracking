"""GET /groups/{group_name} — fetch all ratios in a group with their time series.

For each ratio tagged with the given group, joins stock_data on both legs by
date and returns the resulting ratio series. Computed on read; no precomputed
metrics yet.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Engine, text

from ..deps import db_engine
from ..schemas import GroupResponse, RatioPoint, RatioSeries

router = APIRouter(prefix="/groups", tags=["groups"])


# Single query: every (ratio, date) point for ratios in the group within the
# requested window. Grouped in Python afterward.
_GROUP_QUERY = text(
    """
    SELECT
        r.id            AS ratio_id,
        r.numerator     AS numerator,
        r.denominator   AS denominator,
        n.price_timestamp::date AS bar_date,
        n.close         AS num_close,
        d.close         AS den_close
    FROM ratios r
    JOIN stock_data n
      ON n.ticker_symbol = r.numerator
     AND n.timeframe     = '1d'
    JOIN stock_data d
      ON d.ticker_symbol = r.denominator
     AND d.timeframe     = '1d'
     AND d.price_timestamp = n.price_timestamp
    WHERE r.group_name = :group_name
      AND n.price_timestamp >= (NOW() - make_interval(days => :days))
    ORDER BY r.id, n.price_timestamp
    """
)


@router.get("/{group_name}", response_model=GroupResponse)
def batch_get_group(
    group_name: str,
    days: int = Query(default=120, ge=1, le=365),
    engine: Engine = Depends(db_engine),
) -> GroupResponse:
    with engine.connect() as conn:
        rows = conn.execute(
            _GROUP_QUERY, {"group_name": group_name, "days": days}
        ).all()

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
                date=row.bar_date.isoformat(),
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
