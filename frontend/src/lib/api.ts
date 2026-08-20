/** Typed client for the FastAPI backend. */

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error((detail as { detail?: string }).detail ?? `POST ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface Overview {
  total_revenue: number;
  total_units: number;
  forecast_units_28d: number;
  forecast_revenue_28d: number;
  forecast_accuracy_pct: number;
  history_from: string;
  history_to: string;
  forecast_from: string;
  forecast_to: string;
  series_served: number;
}

export interface SalesPoint { date: string; units: number }
export interface ForecastTotal { date: string; predicted_units: number; expected_revenue: number }
export interface Category {
  cat_id: string; units: number; revenue: number;
  unit_share_pct: number; revenue_share_pct: number;
}
export interface StoreRow {
  store_id: string; state_id: string; units: number; revenue: number;
  forecast_units_28d: number | null; forecast_revenue_28d: number | null;
}
export interface TopProduct {
  item_id: string; cat_id: string; dept_id: string; units: number; revenue: number;
}
export interface WeekdayRow { weekday: string; mean_units: number }
export interface ProductRow { item_id: string; dept_id: string; cat_id: string }
export interface Insight {
  item_id: string; store_id: string; cat_id: string | null;
  recent_daily_units: number; forecast_daily_units: number;
  change_pct: number; forecast_revenue_28d: number;
}
export interface Metrics {
  mae: number; rmse: number; wmape_pct: number; wrmsse: number;
  baseline_rmse: number; improvement_vs_baseline_pct: number; accuracy_pct: number;
}
export interface ModelInfo {
  model_type: string; target: string; horizon_days: number; framing: string;
  trained_rows: number; trained_series: number; trained_from: string; trained_to: string;
  test_window: string[]; last_observed_date: string; features: string[];
  best_params: Record<string, unknown>; library_versions: Record<string, string>;
}
export interface ForecastPoint {
  date: string; predicted_sales: number; predicted_units_exact: number;
  sell_price: number | null; expected_revenue: number | null;
}
export interface ForecastResponse {
  store_id: string; item_id: string; horizon: number; generated_from: string;
  total_predicted_units: number; total_expected_revenue: number;
  forecast: ForecastPoint[];
}

export const api = {
  overview: () => get<Overview>("/api/analytics/overview"),
  metrics: () => get<Metrics>("/api/metrics"),
  modelInfo: () => get<ModelInfo>("/api/model/info"),
  categories: () => get<Category[]>("/api/categories"),
  stores: () => get<StoreRow[]>("/api/stores"),
  products: (catId?: string) =>
    get<ProductRow[]>(`/api/products${catId ? `?cat_id=${encodeURIComponent(catId)}` : ""}`),
  topProducts: (limit = 8) => get<TopProduct[]>(`/api/analytics/top-products?limit=${limit}`),
  weekday: () => get<WeekdayRow[]>("/api/analytics/weekday"),
  history: (start?: string) =>
    get<{ points: SalesPoint[] }>(`/api/sales/history${start ? `?start=${start}` : ""}`)
      .then((r) => r.points),
  seriesHistory: (itemId: string, storeId: string) =>
    get<{ points: SalesPoint[] }>(
      `/api/sales/history?item_id=${encodeURIComponent(itemId)}&store_id=${encodeURIComponent(storeId)}`
    ).then((r) => r.points),
  forecastTotals: () => get<ForecastTotal[]>("/api/forecast/totals"),
  forecast: (item_id: string, store_id: string, horizon = 28) =>
    post<ForecastResponse>("/api/forecast", { item_id, store_id, horizon }),
  attention: (limit = 6) => get<Insight[]>(`/api/insights/attention?limit=${limit}`),
  restock: (limit = 6) => get<Insight[]>(`/api/insights/restock?limit=${limit}`),
};
