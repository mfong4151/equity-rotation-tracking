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


# --- ratios ---

class AddRatioRequest(BaseModel):
    numerator: str = Field(..., min_length=1, max_length=16)
    denominator: str = Field(..., min_length=1, max_length=16)
    group_name: str | None = Field(default=None, max_length=64)

    @field_validator("numerator", "denominator")
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
    points: list[RatioPoint]


class GroupResponse(BaseModel):
    group: str
    days: int
    ratios: list[RatioSeries]
