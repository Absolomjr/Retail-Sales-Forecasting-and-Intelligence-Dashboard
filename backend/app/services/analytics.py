"""Analytics service — the business-intelligence half of the dashboard.

Reads the pre-aggregated tables Part 6 wrote. Nothing here scans the 59M-row
panel at request time; the aggregation already happened once, in the notebook.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..store import store


# ------------------------------------------------------------------ history
def daily_sales(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    df = store.bi("daily_sales").copy()
    df["date"] = pd.to_datetime(df["date"])
    if start:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date"] <= pd.Timestamp(end)]
    return df.sort_values("date")


def series_history(item_id: str, store_id: str) -> pd.DataFrame:
    hist = store.history
    rows = hist[(hist["item_id"] == item_id) & (hist["store_id"] == store_id)]
    return (rows.merge(store.calendar[["d_num", "date"]], on="d_num", how="left")
                .sort_values("d_num")[["date", "sales"]]
                .rename(columns={"sales": "units"}))


# --------------------------------------------------------------- dimensions
def categories() -> pd.DataFrame:
    df = store.bi("category").copy()
    df["unit_share_pct"] = df["units"] / df["units"].sum() * 100
    df["revenue_share_pct"] = df["revenue"] / df["revenue"].sum() * 100
    return df.sort_values("revenue", ascending=False)


def stores() -> pd.DataFrame:
    return store.bi("store").sort_values("revenue", ascending=False)


def top_products(limit: int = 10, cat_id: str | None = None) -> pd.DataFrame:
    df = store.bi("top_products")
    if cat_id:
        df = df[df["cat_id"] == cat_id]
    return df.sort_values("revenue", ascending=False).head(limit)


def weekday_profile() -> pd.DataFrame:
    return store.bi("weekday")


def products(cat_id: str | None = None, search: str | None = None,
             limit: int = 500) -> pd.DataFrame:
    """The items the model can actually serve — not the full 3,049-item catalogue."""
    df = store.series_meta[["item_id", "dept_id", "cat_id"]].drop_duplicates()
    if cat_id:
        df = df[df["cat_id"] == cat_id]
    if search:
        df = df[df["item_id"].str.contains(search, case=False, na=False)]
    return df.sort_values("item_id").head(limit)


# ------------------------------------------------------------------- KPIs
def overview() -> dict:
    cat = store.bi("category")
    daily = daily_sales()
    fc = store.forecast_28d
    meta = store.metadata

    wmape = float(meta["test_metrics"]["WMAPE_%"])
    return {
        "total_revenue": float(cat["revenue"].sum()),
        "total_units": float(cat["units"].sum()),
        "forecast_units_28d": float(fc["predicted_units"].sum()),
        "forecast_revenue_28d": float(fc["expected_revenue"].sum()),
        "forecast_accuracy_pct": max(0.0, 100.0 - wmape),
        "history_from": daily["date"].min().date(),
        "history_to": daily["date"].max().date(),
        "forecast_from": pd.Timestamp(fc["date"].min()).date(),
        "forecast_to": pd.Timestamp(fc["date"].max()).date(),
        "series_served": int(len(store.series_meta)),
    }


# --------------------------------------------------------------- insights
def _catalog() -> pd.DataFrame:
    return store.bi("catalog").copy()


def needs_attention(limit: int = 10) -> pd.DataFrame:
    """Products the model expects to decline — where a buyer should look first.

    Ranked by forecast revenue, not by percentage drop: a 40% fall on a product
    that sells almost nothing is noise, and surfacing it would waste the reader's
    attention.
    """
    df = _catalog()
    df = df[(df["avg_daily_units_28d"] > 0.5) & (df["trend_pct"] < -5)]
    return (df.sort_values("forecast_revenue_28d", ascending=False)
              .head(limit)
              .rename(columns={"avg_daily_units_28d": "recent_daily_units"})
              .assign(forecast_daily_units=lambda d: d["forecast_units_28d"] / 28,
                      change_pct=lambda d: d["trend_pct"]))


def restock(limit: int = 10) -> pd.DataFrame:
    """Products the model expects to grow — candidates for a bigger order."""
    df = _catalog()
    df = df[(df["avg_daily_units_28d"] > 0.5) & (df["trend_pct"] > 5)]
    return (df.sort_values("forecast_revenue_28d", ascending=False)
              .head(limit)
              .rename(columns={"avg_daily_units_28d": "recent_daily_units"})
              .assign(forecast_daily_units=lambda d: d["forecast_units_28d"] / 28,
                      change_pct=lambda d: d["trend_pct"]))


def store_ranking() -> pd.DataFrame:
    """Which store performs best, by revenue, with its forecast attached."""
    hist = stores()
    fc = (store.forecast_28d.groupby("store_id", as_index=False)
                .agg(forecast_units_28d=("predicted_units", "sum"),
                     forecast_revenue_28d=("expected_revenue", "sum")))
    return hist.merge(fc, on="store_id", how="left").sort_values("revenue", ascending=False)


# ---------------------------------------------------------------- metrics
def model_metrics() -> dict:
    meta = store.metadata
    m = meta["test_metrics"]
    baseline = float(meta["baseline_test_rmse"])
    rmse = float(m["RMSE"])
    return {
        "mae": float(m["MAE"]),
        "rmse": rmse,
        "wmape_pct": float(m["WMAPE_%"]),
        "wrmsse": float(meta["test_wrmsse"]),
        "baseline_rmse": baseline,
        "improvement_vs_baseline_pct": (1 - rmse / baseline) * 100,
        "accuracy_pct": max(0.0, 100.0 - float(m["WMAPE_%"])),
    }


def model_info() -> dict:
    meta = store.metadata
    t = meta["trained_on"]
    return {
        "model_type": meta["model_type"],
        "target": meta["target"],
        "horizon_days": meta["horizon_days"],
        "framing": meta["framing"],
        "trained_rows": t["rows"],
        "trained_series": t["series"],
        "trained_from": t["from"],
        "trained_to": t["to"],
        "test_window": meta["test_window"],
        "last_observed_date": meta["last_observed_date"],
        "features": store.features,
        "best_params": meta.get("best_params", {}),
        "library_versions": meta.get("library_versions", {}),
    }
