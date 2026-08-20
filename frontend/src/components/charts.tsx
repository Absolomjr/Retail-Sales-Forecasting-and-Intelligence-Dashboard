import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Category, ForecastTotal, SalesPoint, WeekdayRow } from "../lib/api";
import { SERIES, compactNum, compactUsd, num, shortDate } from "../lib/format";
import { axisProps, gridProps, legendProps, tooltipStyle } from "./primitives";

/**
 * Historical units and the 28-day forecast on one continuous axis.
 *
 * Both series are the same measure in the same unit, so they share one y-axis —
 * a second scale would invent a relationship that is not in the data.
 */
export function HistoryForecastChart({
  history,
  forecast,
}: {
  history: SalesPoint[];
  forecast: ForecastTotal[];
}) {
  const byDate = new Map<string, { date: string; actual?: number; forecast?: number }>();
  for (const p of history) byDate.set(p.date, { date: p.date, actual: p.units });
  for (const f of forecast) {
    const row = byDate.get(f.date) ?? { date: f.date };
    row.forecast = f.predicted_units;
    byDate.set(f.date, row);
  }
  const data = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));

  // Bridge the gap: the forecast series starts where the actuals end, so the
  // two lines join instead of leaving a visual break.
  const lastActual = [...data].reverse().find((d) => d.actual !== undefined);
  if (lastActual) lastActual.forecast = lastActual.actual;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="date" {...axisProps} tickFormatter={shortDate} minTickGap={40} />
        <YAxis {...axisProps} tickFormatter={compactNum} width={48} />
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number, name: string) => [num(v), name]}
          labelFormatter={(l: string) => shortDate(l)}
        />
        <Legend {...legendProps} />
        <Area
          type="monotone"
          dataKey="actual"
          name="Actual units"
          stroke={SERIES[0]}
          strokeWidth={2}
          fill={SERIES[0]}
          fillOpacity={0.08}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="forecast"
          name="Forecast (28 days)"
          stroke={SERIES[1]}
          strokeWidth={2.4}
          strokeDasharray="6 4"
          dot={false}
          connectNulls={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/** Category revenue. One measure, one colour — bar length already carries magnitude. */
export function CategoryChart({ data }: { data: Category[] }) {
  return (
    <ResponsiveContainer width="100%" height={190}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 0, right: 56, left: 4, bottom: 0 }}
        barCategoryGap={14}
      >
        <CartesianGrid {...gridProps} horizontal={false} vertical />
        <XAxis type="number" {...axisProps} tickFormatter={compactUsd} />
        <YAxis type="category" dataKey="cat_id" {...axisProps} width={82} />
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number) => [compactUsd(v), "Revenue"]}
          cursor={{ fill: "rgba(0,0,0,.03)" }}
        />
        <Bar
          dataKey="revenue"
          fill={SERIES[0]}
          radius={[0, 4, 4, 0]}
          label={{
            position: "right",
            formatter: (v: number) => compactUsd(v),
            fill: "#52514e",
            fontSize: 11,
          }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Average units by weekday — the +31% weekend lift, straight from the EDA. */
export function WeekdayChart({ data }: { data: WeekdayRow[] }) {
  const rows = data.map((d) => ({
    ...d,
    short: d.weekday.slice(0, 3),
    weekend: d.weekday === "Saturday" || d.weekday === "Sunday",
  }));
  return (
    <ResponsiveContainer width="100%" height={190}>
      <BarChart data={rows} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="short" {...axisProps} />
        <YAxis {...axisProps} tickFormatter={compactNum} width={44} />
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number) => [num(v), "Avg units/day"]}
          cursor={{ fill: "rgba(0,0,0,.03)" }}
        />
        <Bar dataKey="mean_units" radius={[4, 4, 0, 0]}>
          {rows.map((r) => (
            <Cell key={r.weekday} fill={r.weekend ? SERIES[1] : SERIES[0]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** A single series: its recent actuals, then the model's 28-day forecast. */
export function SeriesForecastChart({
  history,
  forecast,
}: {
  history: SalesPoint[];
  forecast: { date: string; predicted_sales: number }[];
}) {
  const byDate = new Map<string, { date: string; actual?: number; forecast?: number }>();
  for (const p of history) byDate.set(p.date, { date: p.date, actual: p.units });
  for (const f of forecast) {
    const row = byDate.get(f.date) ?? { date: f.date };
    row.forecast = f.predicted_sales;
    byDate.set(f.date, row);
  }
  const data = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  const lastActual = [...data].reverse().find((d) => d.actual !== undefined);
  if (lastActual) lastActual.forecast = lastActual.actual;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="date" {...axisProps} tickFormatter={shortDate} minTickGap={32} />
        <YAxis {...axisProps} allowDecimals={false} width={40} />
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number, name: string) => [num(v), name]}
          labelFormatter={(l: string) => shortDate(l)}
        />
        <Legend {...legendProps} />
        <Line
          type="monotone"
          dataKey="actual"
          name="Actual units"
          stroke={SERIES[0]}
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="forecast"
          name="Forecast"
          stroke={SERIES[1]}
          strokeWidth={2.4}
          strokeDasharray="6 4"
          dot={{ r: 2.5, fill: SERIES[1], strokeWidth: 0 }}
          connectNulls={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
