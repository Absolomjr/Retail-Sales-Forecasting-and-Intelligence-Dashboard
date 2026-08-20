import type { ReactNode } from "react";
import { HAIRLINE, INK_FAINT, INK_MUTED } from "../lib/format";

/** A titled panel. Every chart and table on the page sits in one of these. */
export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 mb-4">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

/** A single headline number. The chart *is* the number — no one-bar bar chart. */
export function Kpi({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="card flex flex-col justify-between min-h-[104px]">
      <span className="label">{label}</span>
      <span
        className="num text-[27px] leading-none font-semibold mt-2 tracking-tight"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </span>
      {hint && <span className="text-[11.5px] text-ink-faint mt-1.5">{hint}</span>}
    </div>
  );
}

export function Skeleton({ height = 260 }: { height?: number }) {
  return (
    <div
      className="w-full rounded-lg animate-pulse"
      style={{ height, background: HAIRLINE }}
      aria-label="Loading"
    />
  );
}

export function ErrorNote({ error }: { error: string }) {
  return (
    <div className="card border-series-8/30 bg-series-8/[0.04]">
      <p className="text-[13px] font-semibold text-series-8">Could not load</p>
      <p className="text-[12px] text-ink-muted mt-1 font-mono break-words">{error}</p>
    </div>
  );
}

/** Shared Recharts styling, so every chart on the page reads as one system. */
export const axisProps = {
  stroke: HAIRLINE,
  tick: { fill: INK_MUTED, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: HAIRLINE },
} as const;

export const gridProps = {
  stroke: HAIRLINE,
  strokeDasharray: "0",
  vertical: false,
} as const;

export const tooltipStyle = {
  contentStyle: {
    background: "#ffffff",
    border: `1px solid ${HAIRLINE}`,
    borderRadius: 10,
    fontSize: 12,
    boxShadow: "0 4px 16px rgba(0,0,0,.07)",
  },
  labelStyle: { color: INK_FAINT, fontSize: 11, marginBottom: 4 },
} as const;

export const legendProps = {
  wrapperStyle: { fontSize: 12, color: INK_MUTED, paddingTop: 8 },
  iconType: "plainline",
  iconSize: 14,
} as const;
