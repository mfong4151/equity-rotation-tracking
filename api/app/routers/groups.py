"""GET /groups/{group_name} — fetch all ratios in a group with their time series.

For each ratio tagged with the given group, joins stock_data on both legs by
date and returns the resulting ratio series. Computed on read; no precomputed
metrics yet.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Engine, and_, select, update, delete as sa_delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from equity_rotation_shared.models import (
    group_settings as group_settings_tbl,
    ratios as ratios_tbl,
    stock_data,
)

from ..deps import db_engine
from ..schemas import (
    GroupListItem,
    GroupResponse,
    RatioPoint,
    RatioSeries,
    RenameGroupRequest,
    ReorderGroupRequest,
    VisibilityRequest,
)

router = APIRouter(prefix="/groups", tags=["groups"])

# Two aliases of stock_data so the numerator and denominator legs of every
# ratio can be joined in a single query.
_num_bars = stock_data.alias("n")
_den_bars = stock_data.alias("d")

_TIMEFRAME = "1d"


@router.get("", response_model=list[GroupListItem])
def list_groups(engine: Engine = Depends(db_engine)) -> list[GroupListItem]:
    # Left join to group_settings so groups without a settings row default to
    # hidden=False. Distinct on name to collapse duplicate ratios per group.
    stmt = (
        select(
            ratios_tbl.c.group_name,
            group_settings_tbl.c.hidden,
        )
        .select_from(
            ratios_tbl.outerjoin(
                group_settings_tbl,
                group_settings_tbl.c.name == ratios_tbl.c.group_name,
            )
        )
        .where(ratios_tbl.c.group_name.is_not(None))
        .distinct()
        .order_by(ratios_tbl.c.group_name)
    )
    with engine.connect() as conn:
        return [
            GroupListItem(name=row[0], hidden=bool(row[1]))
            for row in conn.execute(stmt).all()
        ]


@router.get("/{group_name}", response_model=GroupResponse)
def batch_get_group(
    group_name: str,
    days: int = Query(default=120, ge=1, le=365),
    engine: Engine = Depends(db_engine),
) -> GroupResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # First, fetch the ratios that belong to this group. We always return one
    # entry per ratio even if no bars overlap the window, so the UI can show
    # the ratio with an empty series instead of treating it as a missing group.
    ratios_stmt = (
        select(
            ratios_tbl.c.id,
            ratios_tbl.c.numerator,
            ratios_tbl.c.denominator,
            ratios_tbl.c.pinned,
            ratios_tbl.c.display_order,
        )
        .where(ratios_tbl.c.group_name == group_name)
        .order_by(
            ratios_tbl.c.pinned.desc(),
            ratios_tbl.c.display_order.asc(),
            ratios_tbl.c.id.asc(),
        )
    )

    bars_stmt = (
        select(
            ratios_tbl.c.id.label("ratio_id"),
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
        ratio_rows = conn.execute(ratios_stmt).all()
        bar_rows = conn.execute(bars_stmt).all() if ratio_rows else []

    if not ratio_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown group '{group_name}'",
        )

    points_by_ratio: dict[int, list[RatioPoint]] = defaultdict(list)
    for row in bar_rows:
        den = float(row.den_close)
        if den == 0:
            continue
        points_by_ratio[row.ratio_id].append(
            RatioPoint(
                date=row.bar_ts.date().isoformat(),
                numerator_close=float(row.num_close),
                denominator_close=den,
                ratio=float(row.num_close) / den,
            )
        )

    series = [
        RatioSeries(
            id=r.id,
            numerator=r.numerator,
            denominator=r.denominator,
            pinned=bool(r.pinned),
            points=points_by_ratio.get(r.id, []),
        )
        for r in ratio_rows
    ]
    return GroupResponse(group=group_name, days=days, ratios=series)


@router.delete("/{group_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_name: str,
    cascade: bool = Query(
        default=False,
        description="If true, delete all ratios in this group. Otherwise detach (set group_name = NULL).",
    ),
    engine: Engine = Depends(db_engine),
) -> Response:
    with engine.begin() as conn:
        existing = conn.execute(
            select(ratios_tbl.c.id).where(ratios_tbl.c.group_name == group_name).limit(1)
        ).first()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown group '{group_name}'",
            )
        if cascade:
            conn.execute(sa_delete(ratios_tbl).where(ratios_tbl.c.group_name == group_name))
        else:
            conn.execute(
                update(ratios_tbl)
                .where(ratios_tbl.c.group_name == group_name)
                .values(group_name=None)
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{group_name}", response_model=dict)
def rename_group(
    group_name: str,
    payload: RenameGroupRequest,
    engine: Engine = Depends(db_engine),
) -> dict:
    new_name = payload.new_name.strip()
    if not new_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_name must not be empty",
        )
    if new_name == group_name:
        return {"group": new_name, "updated": 0}
    with engine.begin() as conn:
        existing = conn.execute(
            select(ratios_tbl.c.id).where(ratios_tbl.c.group_name == group_name).limit(1)
        ).first()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown group '{group_name}'",
            )
        collision = conn.execute(
            select(ratios_tbl.c.id).where(ratios_tbl.c.group_name == new_name).limit(1)
        ).first()
        if collision is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Group '{new_name}' already exists. Pick a different name.",
            )
        result = conn.execute(
            update(ratios_tbl)
            .where(ratios_tbl.c.group_name == group_name)
            .values(group_name=new_name)
        )
    return {"group": new_name, "updated": result.rowcount or 0}


@router.put("/{group_name}/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_group(
    group_name: str,
    payload: ReorderGroupRequest,
    engine: Engine = Depends(db_engine),
) -> Response:
    """Set display_order on every ratio in a group from the provided id list.

    The list must be a permutation of the group's current ratio ids. Order
    is 0..N-1 in the order given. Pinned state is unchanged.
    """
    with engine.begin() as conn:
        existing_ids = {
            row.id
            for row in conn.execute(
                select(ratios_tbl.c.id).where(ratios_tbl.c.group_name == group_name)
            ).all()
        }
        if not existing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown group '{group_name}'",
            )
        given = set(payload.ratio_ids)
        if given != existing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ratio_ids must be a permutation of the group's ratio ids",
            )
        for idx, rid in enumerate(payload.ratio_ids):
            conn.execute(
                update(ratios_tbl)
                .where(ratios_tbl.c.id == rid)
                .values(display_order=idx)
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{group_name}/visibility", status_code=status.HTTP_204_NO_CONTENT)
def set_group_visibility(
    group_name: str,
    payload: VisibilityRequest,
    engine: Engine = Depends(db_engine),
) -> Response:
    with engine.begin() as conn:
        existing = conn.execute(
            select(ratios_tbl.c.id).where(ratios_tbl.c.group_name == group_name).limit(1)
        ).first()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown group '{group_name}'",
            )
        stmt = pg_insert(group_settings_tbl).values(
            name=group_name, hidden=payload.hidden
        )
        conn.execute(
            stmt.on_conflict_do_update(
                index_elements=[group_settings_tbl.c.name],
                set_={"hidden": payload.hidden},
            )
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
