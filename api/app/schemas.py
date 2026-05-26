"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# --- tickers ---

class AddTickerRequest(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)

    @field_validator("ticker_symbol")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.strip().upper()


class TickerResponse(BaseModel):
    ticker_symbol: str
    bars_added: int
    latest_bar: str | None


class BatchAddTickerRequest(BaseModel):
    ticker_symbols: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("ticker_symbols")
    @classmethod
    def normalize(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in v:
            sym = s.strip().upper()
            if sym and sym not in seen:
                seen.add(sym)
                out.append(sym)
        if not out:
            raise ValueError("ticker_symbols must contain at least one non-empty symbol")
        return out


class BatchTickerResult(BaseModel):
    ticker_symbol: str
    ok: bool
    bars_added: int | None = None
    latest_bar: str | None = None
    error: str | None = None


class BatchAddTickerResponse(BaseModel):
    results: list[BatchTickerResult]


# --- ratios ---

class AddRatioRequest(BaseModel):
    numerator_stock: str = Field(..., min_length=1, max_length=16)
    denominator_stock: str = Field(..., min_length=1, max_length=16)
    group_name: str | None = Field(default=None, max_length=64)

    @field_validator("numerator_stock", "denominator_stock")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("group_name")
    @classmethod
    def trim_group(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class RatioResponse(BaseModel):
    id: int
    numerator: str
    denominator: str
    group_name: str | None
    created_at: datetime


# --- groups ---

class RatioPoint(BaseModel):
    date: str
    numerator_close: float
    denominator_close: float
    ratio: float


class RatioSeries(BaseModel):
    id: int
    numerator: str
    denominator: str
    pinned: bool = False
    points: list[RatioPoint]


class GroupResponse(BaseModel):
    group: str
    days: int
    ratios: list[RatioSeries]


class RenameGroupRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=64)


class ReorderGroupRequest(BaseModel):
    ratio_ids: list[int] = Field(..., min_length=1)


class PinRatioRequest(BaseModel):
    pinned: bool


class VisibilityRequest(BaseModel):
    hidden: bool


class GroupListItem(BaseModel):
    name: str
    hidden: bool
