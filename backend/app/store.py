"""Artifact store: loads the model and its serving data once, at start-up.

Everything here is produced by Part 6 of `retail_forecasting.ipynb`. Nothing is
computed from the raw CSVs at request time — the API's job is to serve, not to
retrain.
"""

from __future__ import annotations

import json
import logging
from functools import cached_property
from pathlib import Path

import joblib
import pandas as pd

from .config import settings

log = logging.getLogger(__name__)

REQUIRED = [
    "model.pkl",
    "encoders.json",
    "feature_columns.json",
    "model_metadata.json",
    "serving_history.parquet",
    "serving_calendar.parquet",
    "serving_prices.parquet",
    "series_meta.parquet",
    "price_seed.parquet",
    "forecast_28d.parquet",
]


class ArtifactsMissing(RuntimeError):
    """Raised when the notebook has not been run yet."""


class Store:
    """Lazily-loaded, process-wide handle on the model and its data."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or settings.artifacts_dir)

    # ---------------------------------------------------------------- checks
    def verify(self) -> None:
        missing = [f for f in REQUIRED if not (self.root / f).exists()]
        if missing:
            raise ArtifactsMissing(
                f"missing artifacts in {self.root}: {', '.join(missing)}. "
                "Run Part 6 of retail_forecasting.ipynb to generate them."
            )

    # ---------------------------------------------------------------- model
    @cached_property
    def model(self):
        return joblib.load(self.root / "model.pkl")

    @cached_property
    def metadata(self) -> dict:
        return json.loads((self.root / "model_metadata.json").read_text(encoding="utf-8"))

    @cached_property
    def encoders(self) -> dict[str, dict[str, int]]:
        return json.loads((self.root / "encoders.json").read_text(encoding="utf-8"))

    @cached_property
    def feature_spec(self) -> dict:
        return json.loads((self.root / "feature_columns.json").read_text(encoding="utf-8"))

    @property
    def features(self) -> list[str]:
        return self.feature_spec["features"]

    @property
    def event_types(self) -> list[str]:
        return self.feature_spec["event_types"]

    # ------------------------------------------------------------- serving
    @cached_property
    def history(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "serving_history.parquet")

    @cached_property
    def calendar(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "serving_calendar.parquet")

    @cached_property
    def prices(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "serving_prices.parquet")

    @cached_property
    def series_meta(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "series_meta.parquet")

    @cached_property
    def price_seed(self) -> pd.Series:
        seed = pd.read_parquet(self.root / "price_seed.parquet")
        return seed.set_index(["item_id", "store_id"])["price_max"]

    @cached_property
    def forecast_28d(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "forecast_28d.parquet")

    # ------------------------------------------------------------ analytics
    def bi(self, name: str) -> pd.DataFrame:
        """Read one pre-aggregated analytics table (Postgres first, then parquet)."""
        if settings.database_url:
            try:
                return pd.read_sql_table(f"bi_{name}", settings.database_url)
            except Exception:  # noqa: BLE001 - fall back rather than 500 the dashboard
                log.warning("bi_%s not readable from the database; using parquet", name)
        return pd.read_parquet(self.root / f"bi_{name}.parquet")

    # ------------------------------------------------------------ lookups
    @cached_property
    def series_index(self) -> set[tuple[str, str]]:
        return set(zip(self.series_meta["item_id"], self.series_meta["store_id"]))

    @cached_property
    def last_day(self) -> int:
        return int(self.metadata["last_observed_day"])

    def day_to_date(self, d_num: int) -> pd.Timestamp:
        row = self.calendar.loc[self.calendar["d_num"] == d_num, "date"]
        if row.empty:
            raise KeyError(f"d_{d_num} is outside the served calendar")
        return pd.Timestamp(row.iloc[0])

    def warm(self) -> None:
        """Touch every cached property so the first request is not the slow one."""
        self.verify()
        for attr in ("model", "metadata", "encoders", "feature_spec", "history",
                     "calendar", "prices", "series_meta", "price_seed",
                     "forecast_28d", "series_index"):
            getattr(self, attr)
        log.info("artifacts loaded from %s (%d series, model trained to d_%d)",
                 self.root, len(self.series_meta), self.last_day)


store = Store()
