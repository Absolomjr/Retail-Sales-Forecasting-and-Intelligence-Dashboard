"""Forecasting service.

The features are built by ``forecasting.features`` — the *same* module the
notebook trained with. That is deliberate: it is the only way to guarantee the
model sees at serving time exactly what it saw at training time, and the
notebook asserts the equivalence before the model is ever saved.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecasting import features as F

from ..config import settings
from ..store import store


class UnknownSeries(KeyError):
    """The requested (item, store) pair is not one the model can serve."""


def _series_history(item_id: str, store_id: str) -> pd.DataFrame:
    hist = store.history
    rows = hist[(hist["item_id"] == item_id) & (hist["store_id"] == store_id)]
    if rows.empty:
        raise UnknownSeries(f"{item_id} @ {store_id}")
    return rows


def forecast_series(item_id: str, store_id: str, horizon: int = 28) -> pd.DataFrame:
    """Forecast one (item, store) series for the next ``horizon`` days.

    Returns a frame with ``d_num``, ``date``, ``predicted_units``, ``sell_price``
    and ``expected_revenue``.
    """
    horizon = min(horizon, settings.max_horizon)
    history = _series_history(item_id, store_id)
    meta = store.series_meta[(store.series_meta["item_id"] == item_id)
                             & (store.series_meta["store_id"] == store_id)]

    target_days = list(range(store.last_day + 1, store.last_day + 1 + horizon))

    panel = F.horizon_panel(history, meta, target_days)
    built = F.build_features(
        panel,
        store.calendar,
        store.prices,
        store.encoders,
        store.event_types,
        price_max_seed=store.price_seed,
    )
    out = built[built["d_num"].isin(target_days)].copy()

    # A missing price means the product is not on sale that week: no demand to
    # forecast, and the model was never trained on such rows.
    priced = out["sell_price"].notna()
    out["predicted_units"] = np.nan
    if priced.any():
        out.loc[priced, "predicted_units"] = np.clip(
            store.model.predict(out.loc[priced, store.features]), 0, None)

    out["expected_revenue"] = out["predicted_units"] * out["sell_price"]
    out = out.merge(store.calendar[["d_num", "date"]], on="d_num", how="left")
    return out[["d_num", "date", "predicted_units", "sell_price", "expected_revenue"]] \
        .sort_values("d_num").reset_index(drop=True)


def precomputed(item_id: str | None = None, store_id: str | None = None,
                cat_id: str | None = None) -> pd.DataFrame:
    """Slice the 28-day forecast the notebook produced for every served series."""
    fc = store.forecast_28d
    if item_id:
        fc = fc[fc["item_id"] == item_id]
    if store_id:
        fc = fc[fc["store_id"] == store_id]
    if cat_id:
        fc = fc[fc["cat_id"] == cat_id]
    return fc


def forecast_totals() -> pd.DataFrame:
    """Chain-wide daily forecast totals, for the dashboard's headline chart."""
    fc = store.forecast_28d
    return (fc.groupby("date", as_index=False)
              .agg(predicted_units=("predicted_units", "sum"),
                   expected_revenue=("expected_revenue", "sum"))
              .sort_values("date"))
