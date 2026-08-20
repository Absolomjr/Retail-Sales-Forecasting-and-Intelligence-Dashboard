"""HTTP surface. Thin: parse, delegate, serialise."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..schemas import (
    BatchForecastRequest,
    ForecastRequest,
    ForecastResponse,
    ModelInfo,
    ModelMetrics,
    OverviewKpis,
)
from ..services import analytics, forecast as fc_service
from ..store import store

router = APIRouter(prefix="/api")


def _records(df: pd.DataFrame) -> list[dict]:
    return df.replace({float("nan"): None}).to_dict(orient="records")


# ------------------------------------------------------------- dimensions
@router.get("/products", summary="Products the model can forecast")
def get_products(
    cat_id: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Substring match on item_id"),
    limit: int = Query(500, ge=1, le=3000),
):
    return _records(analytics.products(cat_id=cat_id, search=search, limit=limit))


@router.get("/stores", summary="Stores, with lifetime units and revenue")
def get_stores():
    return _records(analytics.store_ranking())


@router.get("/categories", summary="Categories, with unit and revenue shares")
def get_categories():
    return _records(analytics.categories())


# ---------------------------------------------------------------- history
@router.get("/sales/history", summary="Historical sales")
def get_sales_history(
    item_id: str | None = Query(None),
    store_id: str | None = Query(None),
    start: str | None = Query(None, description="ISO date, inclusive"),
    end: str | None = Query(None, description="ISO date, inclusive"),
):
    """Chain-wide daily units, or one series when both ids are supplied."""
    if item_id and store_id:
        if (item_id, store_id) not in store.series_index:
            raise HTTPException(404, f"{item_id} is not served in {store_id}")
        df = analytics.series_history(item_id, store_id)
    elif item_id or store_id:
        raise HTTPException(400, "supply both item_id and store_id, or neither")
    else:
        df = analytics.daily_sales(start, end).rename(columns={"units": "units"})
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return {"item_id": item_id, "store_id": store_id, "points": _records(df)}


# --------------------------------------------------------------- forecast
@router.post("/forecast", response_model=ForecastResponse, summary="Forecast one series")
def post_forecast(req: ForecastRequest):
    if (req.item_id, req.store_id) not in store.series_index:
        raise HTTPException(
            404,
            f"{req.item_id} @ {req.store_id} is not one of the "
            f"{len(store.series_index):,} series this model serves. "
            "See GET /api/products.",
        )
    try:
        df = fc_service.forecast_series(req.item_id, req.store_id, req.horizon)
    except fc_service.UnknownSeries as exc:
        raise HTTPException(404, str(exc)) from exc

    points = [
        {
            "date": pd.Timestamp(r["date"]).date(),
            "predicted_sales": int(round(r["predicted_units"]))
            if pd.notna(r["predicted_units"]) else 0,
            "predicted_units_exact": float(r["predicted_units"])
            if pd.notna(r["predicted_units"]) else 0.0,
            "sell_price": float(r["sell_price"]) if pd.notna(r["sell_price"]) else None,
            "expected_revenue": float(r["expected_revenue"])
            if pd.notna(r["expected_revenue"]) else None,
        }
        for r in df.to_dict(orient="records")
    ]
    return {
        "store_id": req.store_id,
        "item_id": req.item_id,
        "horizon": req.horizon,
        "generated_from": store.day_to_date(store.last_day).date(),
        "total_predicted_units": float(df["predicted_units"].fillna(0).sum()),
        "total_expected_revenue": float(df["expected_revenue"].fillna(0).sum()),
        "forecast": points,
    }


@router.get("/forecast/totals", summary="Chain-wide 28-day forecast")
def get_forecast_totals():
    df = fc_service.forecast_totals().copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return _records(df)


@router.post("/forecast/batch", summary="Pre-computed 28-day forecast for many series")
def post_forecast_batch(req: BatchForecastRequest):
    df = fc_service.precomputed(store_id=req.store_id, cat_id=req.cat_id)
    agg = (df.groupby(["item_id", "store_id", "cat_id"], as_index=False)
             .agg(forecast_units_28d=("predicted_units", "sum"),
                  forecast_revenue_28d=("expected_revenue", "sum"))
             .sort_values("forecast_revenue_28d", ascending=False)
             .head(req.limit))
    return _records(agg)


# ---------------------------------------------------------------- metrics
@router.get("/metrics", response_model=ModelMetrics, summary="Hold-out performance")
def get_metrics():
    return analytics.model_metrics()


@router.get("/model/info", response_model=ModelInfo, summary="What the model is")
def get_model_info():
    return analytics.model_info()


# -------------------------------------------------------------- analytics
@router.get("/analytics/overview", response_model=OverviewKpis, summary="Dashboard KPIs")
def get_overview():
    return analytics.overview()


@router.get("/analytics/top-products", summary="Best sellers by revenue")
def get_top_products(limit: int = Query(10, ge=1, le=200), cat_id: str | None = None):
    return _records(analytics.top_products(limit=limit, cat_id=cat_id))


@router.get("/analytics/weekday", summary="Average units by day of week")
def get_weekday():
    return _records(analytics.weekday_profile())


@router.get("/insights/attention", summary="Products with declining expected demand")
def get_attention(limit: int = Query(10, ge=1, le=100)):
    cols = ["item_id", "store_id", "cat_id", "recent_daily_units",
            "forecast_daily_units", "change_pct", "forecast_revenue_28d"]
    df = analytics.needs_attention(limit)
    return _records(df[[c for c in cols if c in df.columns]])


@router.get("/insights/restock", summary="Products with growing expected demand")
def get_restock(limit: int = Query(10, ge=1, le=100)):
    cols = ["item_id", "store_id", "cat_id", "recent_daily_units",
            "forecast_daily_units", "change_pct", "forecast_revenue_28d"]
    df = analytics.restock(limit)
    return _records(df[[c for c in cols if c in df.columns]])
