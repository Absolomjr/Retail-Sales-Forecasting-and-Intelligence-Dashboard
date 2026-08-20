"""Load the analytics parquet tables into Postgres.

The parquet files stay the source of truth — this just mirrors them so the API
can serve the dashboard's analytics from SQL. Run once after the notebook:

    docker compose run --rm seed
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ARTIFACTS = Path(os.environ.get("RSF_ARTIFACTS_DIR", "artifacts"))
DATABASE_URL = os.environ.get("RSF_DATABASE_URL")

TABLES = ["daily_sales", "category", "store", "top_products", "weekday",
          "weekly_revenue", "catalog"]


def main() -> int:
    if not DATABASE_URL:
        print("RSF_DATABASE_URL is not set; nothing to seed.", file=sys.stderr)
        return 1
    if not ARTIFACTS.exists():
        print(f"{ARTIFACTS} does not exist. Run Part 6 of the notebook first.", file=sys.stderr)
        return 1

    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))

    loaded = 0
    for name in TABLES:
        path = ARTIFACTS / f"bi_{name}.parquet"
        if not path.exists():
            print(f"  skip bi_{name}: not found")
            continue
        df = pd.read_parquet(path)
        df.to_sql(f"bi_{name}", engine, if_exists="replace", index=False)
        print(f"  loaded bi_{name}: {len(df):,} rows")
        loaded += 1

    # The forecast itself is useful in SQL too, for ad-hoc BI queries.
    fc_path = ARTIFACTS / "forecast_28d.parquet"
    if fc_path.exists():
        fc = pd.read_parquet(fc_path)
        fc.to_sql("forecast_28d", engine, if_exists="replace", index=False,
                  chunksize=20_000, method="multi")
        print(f"  loaded forecast_28d: {len(fc):,} rows")
        loaded += 1

    print(f"seeded {loaded} tables into Postgres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
