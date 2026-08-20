"""Request and response models. These *are* the API contract."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- catalogue
class Product(BaseModel):
    item_id: str
    dept_id: str
    cat_id: str


class Store_(BaseModel):
    store_id: str
    state_id: str
    total_units: float
    total_revenue: float


class Category(BaseModel):
    cat_id: str
    units: float
    revenue: float
    unit_share_pct: float
    revenue_share_pct: float


# ------------------------------------------------------------------ history
class SalesPoint(BaseModel):
    date: date
    units: float


class SalesHistory(BaseModel):
    item_id: str | None = None
    store_id: str | None = None
    points: list[SalesPoint]


# ----------------------------------------------------------------- forecast
class ForecastRequest(BaseModel):
    store_id: str = Field(..., examples=["CA_1"])
    item_id: str = Field(..., examples=["FOODS_3_090"])
    horizon: int = Field(28, ge=1, le=28,
                         description="Days ahead. The model is a direct 28-day forecaster.")


class ForecastPoint(BaseModel):
    date: date
    predicted_sales: int
    predicted_units_exact: float
    sell_price: float | None = None
    expected_revenue: float | None = None


class ForecastResponse(BaseModel):
    store_id: str
    item_id: str
    horizon: int
    generated_from: date = Field(..., description="Last day of observed history used")
    total_predicted_units: float
    total_expected_revenue: float
    forecast: list[ForecastPoint]


class BatchForecastRequest(BaseModel):
    store_id: str | None = None
    cat_id: str | None = None
    limit: int = Field(20, ge=1, le=200)


# ------------------------------------------------------------------ metrics
class ModelMetrics(BaseModel):
    mae: float
    rmse: float
    wmape_pct: float
    wrmsse: float
    baseline_rmse: float
    improvement_vs_baseline_pct: float
    accuracy_pct: float = Field(..., description="100 - WMAPE, the dashboard headline")


class ModelInfo(BaseModel):
    model_type: str
    target: str
    horizon_days: int
    framing: str
    trained_rows: int
    trained_series: int
    trained_from: date
    trained_to: date
    test_window: list[date]
    last_observed_date: date
    features: list[str]
    best_params: dict
    library_versions: dict


# ---------------------------------------------------------------- analytics
class OverviewKpis(BaseModel):
    total_revenue: float
    total_units: float
    forecast_units_28d: float
    forecast_revenue_28d: float
    forecast_accuracy_pct: float
    history_from: date
    history_to: date
    forecast_from: date
    forecast_to: date
    series_served: int


class InsightRow(BaseModel):
    item_id: str
    store_id: str
    cat_id: str | None = None
    recent_daily_units: float
    forecast_daily_units: float
    change_pct: float
    forecast_revenue_28d: float
