# shared

Small installable package that both [api](../api) and [offline-jobs](../offline-jobs) depend on. Defines the single source of truth (Python side) for:

- **SQLAlchemy Core Table objects** (`models.py`) mirroring [api/sql/schema.sql](../api/sql/schema.sql).
- **Engine factory** (`db.py`) reading `DATABASE_URL`.
- **Polygon ingestion** (`polygon.py`): `ensure_ticker_tracked()` is the one function used by the collector job, `add_ticker`, and `add_ratio`.
- **Env helpers** (`env.py`).

## Use

From either consumer:

```bash
pip install -e ../shared
```

Then:

```python
from equity_rotation_shared import get_engine
from equity_rotation_shared.models import tickers, stock_data, ratios
from equity_rotation_shared.polygon import ensure_ticker_tracked
```

## Note on schema source of truth

`api/sql/schema.sql` is authoritative. `models.py` *mirrors* it — keep them in sync by hand. We deliberately do **not** use Alembic/autogeneration so the schema stays language-agnostic and the API can be reimplemented in any language later.
