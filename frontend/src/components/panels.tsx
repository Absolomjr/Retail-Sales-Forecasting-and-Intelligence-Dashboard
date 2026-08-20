import { useEffect, useState } from "react";
import type { Category, Insight, Metrics, ModelInfo, ProductRow, StoreRow, TopProduct } from "../lib/api";
import { api } from "../lib/api";
import type { ForecastResponse, SalesPoint } from "../lib/api";
import { SERIES, compactUsd, longDate, num, pct, signedPct, usd } from "../lib/format";
import { SeriesForecastChart } from "./charts";
import { Card, Skeleton } from "./primitives";

/** Best sellers. A ranked list, not a chart — the order *is* the message. */
export function TopProducts({ rows }: { rows: TopProduct[] }) {
  const max = Math.max(...rows.map((r) => r.revenue), 1);
  return (
    <ol className="space-y-2.5">
      {rows.map((r, i) => (
        <li key={r.item_id} className="flex items-center gap-3">
          <span className="num text-[11px] text-ink-faint w-4 shrink-0">{i + 1}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[12.5px] font-medium truncate">{r.item_id}</span>
              <span className="num text-[12px] text-ink-muted shrink-0">
                {compactUsd(r.revenue)}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-hairline mt-1.5 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${(r.revenue / max) * 100}%`, background: SERIES[0] }}
              />
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

/** Store league table, with each store's own 28-day forecast beside its history. */
export function StoreTable({ rows }: { rows: StoreRow[] }) {
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-[12.5px] min-w-[420px]">
        <thead>
          <tr className="table-head border-b border-hairline">
            <th className="text-left font-semibold py-2 px-1">Store</th>
            <th className="text-left font-semibold py-2 px-1">State</th>
            <th className="text-right font-semibold py-2 px-1">Revenue</th>
            <th className="text-right font-semibold py-2 px-1">Units</th>
            <th className="text-right font-semibold py-2 px-1">Forecast 28d</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.store_id} className="border-b border-hairline/60 last:border-0">
              <td className="py-2 px-1 font-medium">
                {i === 0 && (
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full mr-2 align-middle"
                    style={{ background: SERIES[1] }}
                    aria-label="Top performer"
                  />
                )}
                {r.store_id}
              </td>
              <td className="py-2 px-1 text-ink-muted">{r.state_id}</td>
              <td className="py-2 px-1 text-right num">{compactUsd(r.revenue)}</td>
              <td className="py-2 px-1 text-right num text-ink-muted">
                {(r.units / 1e6).toFixed(1)}M
              </td>
              <td className="py-2 px-1 text-right num">
                {r.forecast_units_28d != null ? num(r.forecast_units_28d) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Business intelligence: which products need attention, which need restocking. */
export function InsightList({ rows, tone }: { rows: Insight[]; tone: "down" | "up" }) {
  const colour = tone === "down" ? SERIES[7] : SERIES[2];
  if (!rows.length) {
    return <p className="text-[12.5px] text-ink-faint">No series crossed the ±5% threshold.</p>;
  }
  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li
          key={`${r.item_id}-${r.store_id}`}
          className="flex items-center justify-between gap-3 border-b border-hairline/60 pb-2.5 last:border-0 last:pb-0"
        >
          <div className="min-w-0">
            <p className="text-[12.5px] font-medium truncate">{r.item_id}</p>
            <p className="text-[11px] text-ink-faint">
              {r.store_id} · {num(r.recent_daily_units, 1)} → {num(r.forecast_daily_units, 1)}{" "}
              units/day
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="num text-[13px] font-semibold" style={{ color: colour }}>
              {signedPct(r.change_pct, 0)}
            </p>
            <p className="num text-[11px] text-ink-faint">{compactUsd(r.forecast_revenue_28d)}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Hold-out performance and provenance — what the number on the KPI tile means. */
export function ModelPanel({ metrics, info }: { metrics: Metrics; info: ModelInfo }) {
  const stats: [string, string][] = [
    ["MAE", num(metrics.mae, 3)],
    ["RMSE", num(metrics.rmse, 3)],
    ["WMAPE", pct(metrics.wmape_pct)],
    ["WRMSSE", num(metrics.wrmsse, 3)],
    ["Baseline RMSE", num(metrics.baseline_rmse, 3)],
    ["vs baseline", signedPct(metrics.improvement_vs_baseline_pct)],
  ];
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-3 gap-x-4 gap-y-3">
        {stats.map(([k, v]) => (
          <div key={k}>
            <dt className="label">{k}</dt>
            <dd className="num text-[15px] font-semibold mt-0.5">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="border-t border-hairline pt-3 space-y-1 text-[11.5px] text-ink-muted">
        <p>
          <span className="text-ink-faint">Model </span>
          {info.model_type} · {info.horizon_days}-day {info.framing.split(" - ")[0]}
        </p>
        <p>
          <span className="text-ink-faint">Trained </span>
          {num(info.trained_rows)} rows over {num(info.trained_series)} series,{" "}
          {longDate(info.trained_from)} → {longDate(info.trained_to)}
        </p>
        <p>
          <span className="text-ink-faint">Tested </span>
          {longDate(info.test_window[0])} → {longDate(info.test_window[1])} · never used for tuning
        </p>
      </div>
    </div>
  );
}

/** The interactive half: pick a series, generate a live 28-day forecast. */
export function ForecastPanel({ stores, categories }: { stores: StoreRow[]; categories: Category[] }) {
  const [storeId, setStoreId] = useState("");
  const [itemId, setItemId] = useState("");
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [category, setCategory] = useState("");
  const [result, setResult] = useState<ForecastResponse | null>(null);
  const [history, setHistory] = useState<SalesPoint[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.products(category || undefined).then((rows) => {
      setProducts(rows);
      setItemId((current) => (rows.some((r) => r.item_id === current) ? current : rows[0]?.item_id ?? ""));
    });
  }, [category]);

  useEffect(() => {
    if (!storeId && stores.length) setStoreId(stores[0].store_id);
  }, [stores, storeId]);

  // Derived from the full category list, never from `products` - `products` is
  // itself filtered by the selected category, so deriving the options from it
  // collapsed the dropdown to the current choice and stranded the reader there.
  const catIds = [...categories].map((c) => c.cat_id).sort();

  async function generate() {
    if (!itemId || !storeId) return;
    setBusy(true);
    setError(null);
    try {
      const [fc, hist] = await Promise.all([
        api.forecast(itemId, storeId, 28),
        api.seriesHistory(itemId, storeId),
      ]);
      setResult(fc);
      setHistory(hist.slice(-42));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="Generate a forecast"
      subtitle="Runs the model live — features are rebuilt by the same code that trained it"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:items-end">
        <div>
          <label className="label block mb-1.5" htmlFor="store">Store</label>
          <select
            id="store"
            className="select"
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
          >
            {stores.map((s) => (
              <option key={s.store_id} value={s.store_id}>
                {s.store_id} ({s.state_id})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label block mb-1.5" htmlFor="cat">Category</label>
          <select
            id="cat"
            className="select"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {catIds.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label block mb-1.5" htmlFor="item">Product</label>
          <select
            id="item"
            className="select"
            value={itemId}
            onChange={(e) => setItemId(e.target.value)}
          >
            {products.map((p) => (
              <option key={p.item_id} value={p.item_id}>{p.item_id}</option>
            ))}
          </select>
        </div>
        <button className="btn-primary h-[38px]" onClick={generate} disabled={busy || !itemId}>
          {busy ? "Forecasting…" : "Generate 28-day forecast"}
        </button>
      </div>

      {error && (
        <p className="mt-4 text-[12px] text-series-8 font-mono break-words">{error}</p>
      )}

      {busy && !result && <div className="mt-5"><Skeleton height={260} /></div>}

      {result && (
        <div className="mt-5">
          <div className="flex flex-wrap gap-x-8 gap-y-2 mb-4">
            <Stat label="Predicted units (28d)" value={num(result.total_predicted_units)} />
            <Stat label="Expected revenue" value={usd(result.total_expected_revenue)} />
            <Stat label="Forecast from" value={longDate(result.generated_from)} />
          </div>
          <SeriesForecastChart history={history} forecast={result.forecast} />
        </div>
      )}
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p className="num text-[19px] font-semibold mt-0.5">{value}</p>
    </div>
  );
}
