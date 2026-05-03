"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { downloadReportCsv, getReportSummary, getReportTrend } from "@/lib/api";
import type { SummaryOut, TrendOut } from "@/types";

type Range = "24h" | "7d" | "30d";

interface AnalyticsPanelProps {
  token: string;
}

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function rangeToParams(range: Range): { from: string; to: string; interval: string; granularity: string } {
  const to = new Date();
  const from = new Date(to);
  if (range === "24h") {
    from.setDate(from.getDate() - 1);
    return { from: toDateStr(from), to: toDateStr(to), interval: "hour", granularity: "day" };
  } else if (range === "7d") {
    from.setDate(from.getDate() - 7);
    return { from: toDateStr(from), to: toDateStr(to), interval: "hour", granularity: "day" };
  } else {
    from.setDate(from.getDate() - 30);
    return { from: toDateStr(from), to: toDateStr(to), interval: "day", granularity: "day" };
  }
}

function formatTs(ts: string, range: Range): string {
  const d = new Date(ts);
  if (range === "30d") return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function topEntry(map: Record<string, number>): string {
  const entries = Object.entries(map);
  if (!entries.length) return "—";
  return entries.sort((a, b) => b[1] - a[1])[0][0];
}

function mergedByZone(buckets: SummaryOut["buckets"]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const b of buckets) {
    for (const [k, v] of Object.entries(b.by_zone)) {
      out[k] = (out[k] ?? 0) + v;
    }
  }
  return out;
}

function mergedByPpe(buckets: SummaryOut["buckets"]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const b of buckets) {
    for (const [k, v] of Object.entries(b.by_ppe)) {
      out[k] = (out[k] ?? 0) + v;
    }
  }
  return out;
}

export default function AnalyticsPanel({ token }: AnalyticsPanelProps) {
  const [range, setRange] = useState<Range>("24h");
  const [summary, setSummary] = useState<SummaryOut | null>(null);
  const [trend, setTrend] = useState<TrendOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const { from, to, interval, granularity } = rangeToParams(range);
    setLoading(true);
    setError(null);
    Promise.all([
      getReportSummary(token, from, to, granularity),
      getReportTrend(token, from, to, interval),
    ])
      .then(([s, t]) => { setSummary(s); setTrend(t); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, range]);

  async function handleExport() {
    const { from, to } = rangeToParams(range);
    setExporting(true);
    try { await downloadReportCsv(token, from, to); } catch { /* silent */ } finally { setExporting(false); }
  }

  const violations = summary?.totals?.ppe_violations ?? 0;
  const topZone = summary ? topEntry(mergedByZone(summary.buckets)) : "—";
  const topPpe = summary ? topEntry(mergedByPpe(summary.buckets)) : "—";
  const totalEvents = summary
    ? summary.buckets.reduce((s, b) => s + b.ppe_violations + b.zone_enter + b.zone_exit, 0)
    : 0;

  const chartData = trend?.series.map((p) => ({
    ts: p.ts, count: p.count, label: formatTs(p.ts, range),
  })) ?? [];

  const ANALYTICS_CSS = `
    .an-panel { background:var(--s1); border-top:1px solid var(--border); padding:14px; }
    .an-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
    .an-title { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:rgba(255,255,255,.22); }
    .an-controls { display:flex; align-items:center; gap:6px; }
    .an-range-grp { display:flex; background:var(--s2); border:1px solid var(--border); border-radius:4px; overflow:hidden; }
    .an-range-btn { font-size:10px; padding:3px 9px; background:none; border:none; cursor:pointer; color:rgba(255,255,255,.28); font-family:inherit; transition:color .15s,background .15s; }
    .an-range-btn.active { color:var(--green); background:rgba(74,222,128,.06); }
    .an-range-btn:hover:not(.active) { color:rgba(255,255,255,.55); }
    .an-export-btn { font-size:10px; color:var(--text3); background:none; border:1px solid var(--border); border-radius:4px; padding:3px 9px; cursor:pointer; transition:color .15s,border-color .15s; font-family:inherit; }
    .an-export-btn:hover:not(:disabled) { color:var(--text2); border-color:var(--border2); }
    .an-export-btn:disabled { opacity:.3; cursor:default; }
    .an-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; margin-bottom:12px; }
    .an-stat { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.05); border-radius:5px; padding:10px 12px; }
    .an-stat-lbl { font-size:9px; font-weight:500; letter-spacing:.08em; text-transform:uppercase; color:rgba(255,255,255,.22); margin-bottom:5px; }
    .an-stat-val { font-size:18px; font-weight:700; font-family:monospace; color:var(--text); line-height:1; }
    .an-stat-val.text { font-size:14px; font-family:inherit; }
    .an-skeleton { height:18px; width:48px; background:rgba(255,255,255,.06); border-radius:3px; }
    .an-chart-wrap { background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.05); border-radius:5px; padding:12px; }
    .an-chart-lbl { font-size:10px; color:rgba(255,255,255,.22); margin-bottom:10px; }
    .an-chart-empty { height:160px; display:flex; align-items:center; justify-content:center; font-size:11px; color:var(--text3); }
    .an-error { font-size:11px; color:var(--red); margin-bottom:10px; }
  `;

  return (
    <>
      <style>{ANALYTICS_CSS}</style>
      <section className="an-panel">
        <div className="an-head">
          <span className="an-title">Analytics</span>
          <div className="an-controls">
            <div className="an-range-grp">
              {(["24h", "7d", "30d"] as Range[]).map((r) => (
                <button
                  key={r}
                  className={`an-range-btn${range === r ? " active" : ""}`}
                  onClick={() => setRange(r)}
                >{r}</button>
              ))}
            </div>
            <button
              className="an-export-btn"
              onClick={handleExport}
              disabled={exporting || loading}
            >
              {exporting ? "Exporting…" : "↓ CSV"}
            </button>
          </div>
        </div>

        {error && <p className="an-error">{error}</p>}

        <div className="an-stats">
          {[
            { label: "PPE Violations", value: loading ? null : violations, text: false },
            { label: "Total Events", value: loading ? null : totalEvents, text: false },
            { label: "Top Zone", value: loading ? null : topZone, text: true },
            { label: "Top Missing PPE", value: loading ? null : topPpe, text: true },
          ].map(({ label, value, text }) => (
            <div key={label} className="an-stat">
              <div className="an-stat-lbl">{label}</div>
              {value === null
                ? <div className="an-skeleton" />
                : <div className={`an-stat-val${text ? " text" : ""}`}>{value}</div>
              }
            </div>
          ))}
        </div>

        <div className="an-chart-wrap">
          <p className="an-chart-lbl">PPE Violations — last {range}</p>
          {loading ? (
            <div style={{ height: 160, background: "rgba(255,255,255,.04)", borderRadius: 3 }} />
          ) : chartData.length === 0 ? (
            <div className="an-chart-empty">No violations in this period</div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c1c1c" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "#555", fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#555", fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "var(--s1)", border: "1px solid var(--border2)", borderRadius: "5px", fontSize: "11px", color: "var(--text2)" }}
                  itemStyle={{ color: "var(--red)" }}
                  cursor={{ stroke: "#2e2e2e" }}
                />
                <Line type="monotone" dataKey="count" stroke="#f87171" strokeWidth={1.5} dot={false} activeDot={{ r: 3, fill: "#f87171" }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
    </>
  );
}

