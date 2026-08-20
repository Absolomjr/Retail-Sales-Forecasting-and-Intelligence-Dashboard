import { useEffect, useState } from "react";
import type {
  Category,
  ForecastTotal,
  Insight,
  Metrics,
  ModelInfo,
  Overview,
  SalesPoint,
  StoreRow,
  TopProduct,
  WeekdayRow,
} from "./lib/api";
import { api } from "./lib/api";
import { compactNum, compactUsd, longDate, pct } from "./lib/format";
import { CategoryChart, HistoryForecastChart, WeekdayChart } from "./components/charts";
import { ForecastPanel, InsightList, ModelPanel, StoreTable, TopProducts } from "./components/panels";
import { Card, ErrorNote, Kpi, Skeleton } from "./components/primitives";

interface Data {
  overview: Overview;
  metrics: Metrics;
  info: ModelInfo;
  categories: Category[];
  stores: StoreRow[];
  topProducts: TopProduct[];
  weekday: WeekdayRow[];
  history: SalesPoint[];
  forecastTotals: ForecastTotal[];
  attention: Insight[];
  restock: Insight[];
}

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.overview(),
      api.metrics(),
      api.modelInfo(),
      api.categories(),
      api.stores(),
      api.topProducts(8),
      api.weekday(),
      // Two years of daily history keeps the headline chart legible; the API
      // holds all five.
      api.history("2014-06-01"),
      api.forecastTotals(),
      api.attention(6),
      api.restock(6),
    ])
      .then(([overview, metrics, info, categories, stores, topProducts, weekday,
              history, forecastTotals, attention, restock]) =>
        setData({ overview, metrics, info, categories, stores, topProducts, weekday,
                  history, forecastTotals, attention, restock }))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <Shell>
        <ErrorNote error={error} />
        <p className="text-[12.5px] text-ink-muted mt-4">
          The API must be running and the notebook's <code className="font-mono">artifacts/</code>{" "}
          folder must exist. Try <code className="font-mono">docker compose up</code>, or{" "}
          <code className="font-mono">cd backend &amp;&amp; uvicorn app.main:app --reload</code>.
        </p>
      </Shell>
    );
  }

  if (!data) {
    return (
      <Shell>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} height={104} />)}
        </div>
        <Skeleton height={360} />
      </Shell>
    );
  }

  const { overview: o, metrics: m } = data;

  return (
    <Shell
      subtitle={`${longDate(o.history_from)} – ${longDate(o.history_to)} observed · forecasting ${longDate(o.forecast_from)} – ${longDate(o.forecast_to)}`}
    >
      {/* ---------------------------------------------------------- KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi
          label="Total sales"
          value={compactUsd(o.total_revenue)}
          hint={`${compactNum(o.total_units)} units, all stores`}
        />
        <Kpi
          label="Forecast revenue (28d)"
          value={compactUsd(o.forecast_revenue_28d)}
          hint={`${compactNum(o.forecast_units_28d)} units across ${compactNum(o.series_served)} series`}
        />
        <Kpi
          label="Forecast accuracy"
          value={pct(o.forecast_accuracy_pct)}
          hint="100 − WMAPE on the untouched test window"
          accent="#1baf7a"
        />
        <Kpi
          label="Beats naive baseline by"
          value={pct(m.improvement_vs_baseline_pct)}
          hint={`RMSE ${m.rmse.toFixed(2)} vs ${m.baseline_rmse.toFixed(2)}`}
          accent="#eb6834"
        />
      </div>

      {/* ------------------------------------------- history + forecast */}
      <Card
        className="mt-4"
        title="Historical sales and 28-day forecast"
        subtitle="Daily units chain-wide; the dashed segment is the model's forecast"
      >
        <HistoryForecastChart history={data.history} forecast={data.forecastTotals} />
      </Card>

      {/* ------------------------------------------------- forecast tool */}
      <div className="mt-4">
        <ForecastPanel stores={data.stores} categories={data.categories} />
      </div>

      {/* ---------------------------------------------- analytics strip */}
      <div className="grid gap-4 mt-4 lg:grid-cols-3">
        <Card title="Top products" subtitle="By lifetime revenue">
          <TopProducts rows={data.topProducts} />
        </Card>
        <Card title="Sales by category" subtitle="Lifetime revenue">
          <CategoryChart data={data.categories} />
          <p className="text-[11.5px] text-ink-faint mt-3">
            FOODS is {data.categories[0]?.unit_share_pct.toFixed(0)}% of units but{" "}
            {data.categories[0]?.revenue_share_pct.toFixed(0)}% of revenue — the cheapest category.
          </p>
        </Card>
        <Card title="Sales by weekday" subtitle="Average units per trading day; weekend highlighted">
          <WeekdayChart data={data.weekday} />
        </Card>
      </div>

      {/* ------------------------------------------------ stores + model */}
      <div className="grid gap-4 mt-4 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Store performance"
              subtitle="Lifetime revenue with the next 28 days forecast">
          <StoreTable rows={data.stores} />
        </Card>
        <Card title="Model performance" subtitle="Measured on data the model never saw">
          <ModelPanel metrics={data.metrics} info={data.info} />
        </Card>
      </div>

      {/* --------------------------------------------------- BI insights */}
      <div className="grid gap-4 mt-4 lg:grid-cols-2">
        <Card title="Needs attention" subtitle="Declining expected demand, ranked by revenue at risk">
          <InsightList rows={data.attention} tone="down" />
        </Card>
        <Card title="Stock up" subtitle="Growing expected demand, ranked by revenue opportunity">
          <InsightList rows={data.restock} tone="up" />
        </Card>
      </div>

      <footer className="text-[11.5px] text-ink-faint mt-8 pb-4">
        Forecasts cover the {data.overview.series_served.toLocaleString()} product-store series the
        model was trained on (a stratified sample of the M5 dataset). Model:{" "}
        {data.info.model_type}, {data.info.horizon_days}-day direct horizon.
      </footer>
    </Shell>
  );
}

function Shell({ children, subtitle }: { children: React.ReactNode; subtitle?: string }) {
  return (
    <div className="min-h-screen">
      <header className="bg-surface-raised border-b border-hairline">
        <div className="max-w-[1400px] mx-auto px-5 py-5">
          <h1 className="text-[19px] font-bold tracking-tight">Retail Sales Forecasting</h1>
          <p className="text-[12px] text-ink-faint mt-0.5">
            {subtitle ?? "Demand intelligence for 10 stores across CA, TX and WI"}
          </p>
        </div>
      </header>
      <main className="max-w-[1400px] mx-auto px-5 py-5">{children}</main>
    </div>
  );
}
