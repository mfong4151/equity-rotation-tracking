-- Equity Rotation Tracking — generic OHLC store (PostgreSQL)
--
-- Three tables:
--   tickers     : the (small) source-of-truth list of symbols the collector
--                 should ingest each day. CRUD is managed by the API / frontend.
--   stock_data  : generic OHLC store, one row per (ticker, timeframe, bar time).
--                 Kept extensible by the `timeframe` column so daily/hourly/5m
--                 bars can all live in the same table.
--   ratios      : user-defined (numerator, denominator) ratios, optionally
--                 tagged with a group_name for batch retrieval.
--

-- =============================================================================
-- tickers: source-of-truth list of symbols being tracked
-- =============================================================================
CREATE TABLE IF NOT EXISTS tickers (
    ticker_symbol  TEXT        PRIMARY KEY,                     -- e.g. 'SPY'
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    added_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_ingest_at TIMESTAMPTZ                                  -- updated by collector
);

CREATE INDEX IF NOT EXISTS idx_tickers_active ON tickers(is_active);

-- Default seed: a tiny baseline so the collector has something to do on a
-- fresh install. Idempotent (ON CONFLICT) so re-running schema.sql is safe.
INSERT INTO tickers (ticker_symbol) VALUES
    ('SPY'),
    ('QQQ'),
    ('IWM')
ON CONFLICT (ticker_symbol) DO NOTHING;


-- =============================================================================
-- stock_data: generic OHLC bars
-- =============================================================================
CREATE TABLE IF NOT EXISTS stock_data (
    ticker_symbol   TEXT          NOT NULL REFERENCES tickers(ticker_symbol) ON DELETE CASCADE,
    timeframe       TEXT          NOT NULL,                            -- e.g. '1d', '1h', '5m'
    price_timestamp TIMESTAMPTZ   NOT NULL,                            -- when the bar occurred
    open            NUMERIC(18,6) NOT NULL,
    high            NUMERIC(18,6) NOT NULL,
    low             NUMERIC(18,6) NOT NULL,
    close           NUMERIC(18,6) NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),             -- when this row was inserted

    PRIMARY KEY (ticker_symbol, timeframe, price_timestamp)
);

CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_time
    ON stock_data (ticker_symbol, timeframe, price_timestamp DESC);


-- =============================================================================
-- ratios: user-defined ratio pairs, optionally tagged with a group
-- =============================================================================
-- group_name is just a label on the ratio. The "tickers in a group" are
-- transitively defined as "any ticker appearing as numerator or denominator in
-- a ratio with that group". No separate ticker<->group table needed.
--
-- A given (numerator, denominator) pair can appear in multiple groups (e.g.
-- 'NVDA/SOXX' in 'Semiconductors' and in 'AI Plays'), so the uniqueness
-- constraint includes group_name. group_name is nullable for ungrouped ratios.
CREATE TABLE IF NOT EXISTS ratios (
    id           BIGSERIAL   PRIMARY KEY,
    numerator    TEXT        NOT NULL REFERENCES tickers(ticker_symbol) ON DELETE CASCADE,
    denominator  TEXT        NOT NULL REFERENCES tickers(ticker_symbol) ON DELETE CASCADE,
    group_name   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ratios_distinct_legs CHECK (numerator <> denominator),
    CONSTRAINT ratios_unique_in_group UNIQUE (numerator, denominator, group_name)
);

CREATE INDEX IF NOT EXISTS idx_ratios_group ON ratios(group_name);
