"""SQLAlchemy Core Table objects mirroring api/sql/schema.sql.

These are *not* the source of truth for the schema — schema.sql is. These
mirror it so we get parameterized queries, type coercion, and a single place
to import column references from.

Keep in sync with api/sql/schema.sql by hand.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func

metadata = MetaData()

tickers = Table(
    "tickers",
    metadata,
    Column("ticker_symbol", Text, primary_key=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("added_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column("last_ingest_at", TIMESTAMP(timezone=True)),
)

stock_data = Table(
    "stock_data",
    metadata,
    Column(
        "ticker_symbol",
        Text,
        ForeignKey("tickers.ticker_symbol", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("timeframe", Text, nullable=False),
    Column("price_timestamp", TIMESTAMP(timezone=True), nullable=False),
    Column("open", Numeric(18, 6), nullable=False),
    Column("high", Numeric(18, 6), nullable=False),
    Column("low", Numeric(18, 6), nullable=False),
    Column("close", Numeric(18, 6), nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("ticker_symbol", "timeframe", "price_timestamp"),
)

ratios = Table(
    "ratios",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "numerator",
        Text,
        ForeignKey("tickers.ticker_symbol", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "denominator",
        Text,
        ForeignKey("tickers.ticker_symbol", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("group_name", Text),
    Column("pinned", Boolean, nullable=False, server_default="false"),
    Column("display_order", Integer, nullable=False, server_default="0"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("numerator <> denominator", name="ratios_distinct_legs"),
    UniqueConstraint("numerator", "denominator", "group_name", name="ratios_unique_in_group"),
)

group_settings = Table(
    "group_settings",
    metadata,
    Column("name", Text, primary_key=True),
    Column("hidden", Boolean, nullable=False, server_default="false"),
)
