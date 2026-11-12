/** Reports (Template Method on the backend): every report has the same shape, so one page renders any of them. */
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { StateMessage } from "../components/StateMessage";
import { adminApi, type Report, type ReportCell, type ReportChart, type ValueFormat } from "./api";

// Categorical slots, validated for colour-blind separation against the dark surface.
const SERIES_COLORS = ["#3987e5", "#d95926", "#199e70"];
const AXIS = { stroke: "var(--border)", tick: { fill: "var(--text-muted)", fontSize: 12 } };
const TOOLTIP = {
  contentStyle: { background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8 },
  labelStyle: { color: "var(--text)" },
  itemStyle: { color: "var(--text)" },
  cursor: { fill: "rgb(255 255 255 / 0.05)" },
};

// Legend text stays in the text colour; the swatch next to it carries the series identity.
const legendText = (value: string) => <span style={{ color: "var(--text-muted)" }}>{value}</span>;

const PRESETS = [7, 30, 90, 365];
const shortDay = new Intl.DateTimeFormat("uk-UA", { day: "numeric", month: "short", timeZone: "UTC" });
const shortMonth = new Intl.DateTimeFormat("uk-UA", { month: "short", year: "numeric", timeZone: "UTC" });
const number = new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 1 });
const money = new Intl.NumberFormat("uk-UA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function formatValue(value: ReportCell, format: ValueFormat | "text"): string {
  if (typeof value === "string") return value;
  switch (format) {
    case "money": return `${money.format(value)} грн`;
    case "percent": return `${number.format(value)} %`;
    case "hours": return `${number.format(value)} год`;
    default: return number.format(value);
  }
}

const isoDay = (date: Date) => date.toISOString().slice(0, 10);

function daysAgo(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - (days - 1));
  return isoDay(date);
}

/** Chart x labels: "2026-11-05" → "5 лист.", "2026-11" (monthly buckets) → "лист. 2026 р."; other values as is. */
function formatDay(value: ReportCell): string {
  if (typeof value !== "string") return String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return shortDay.format(new Date(`${value}T00:00:00Z`));
  if (/^\d{4}-\d{2}$/.test(value)) return shortMonth.format(new Date(`${value}-01T00:00:00Z`));
  return value;
}

export function AdminReportsPage() {
  const [params, setParams] = useSearchParams();
  const code = params.get("report") ?? "popularity";
  const dateTo = params.get("to") ?? isoDay(new Date());
  const dateFrom = params.get("from") ?? daysAgo(30);

  const list = useQuery({ queryKey: ["admin", "reports"], queryFn: adminApi.reports });
  const report = useQuery({
    queryKey: ["admin", "reports", code, dateFrom, dateTo],
    queryFn: () => adminApi.report(code, dateFrom, dateTo),
    placeholderData: (previous) => (previous?.code === code ? previous : undefined),
  });

  const update = (changes: Record<string, string>) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      Object.entries(changes).forEach(([key, value]) => next.set(key, value));
      return next;
    });

  const today = isoDay(new Date());
  const activePreset = dateTo === today ? PRESETS.find((days) => daysAgo(days) === dateFrom) : undefined;

  return (
    <div className="admin__section">
      <div className="chips" role="tablist" aria-label="Звіт">
        {list.data?.map((item) => (
          <button key={item.code} role="tab" aria-selected={item.code === code} title={item.description}
                  className={`chip${item.code === code ? " chip--active" : ""}`}
                  onClick={() => update({ report: item.code })}>
            {item.title}
          </button>
        ))}
      </div>

      <div className="reports__filters">
        <div className="chips">
          {PRESETS.map((days) => (
            <button key={days} className={`chip${activePreset === days ? " chip--active" : ""}`}
                    onClick={() => update({ from: daysAgo(days), to: today })}>
              {days === 365 ? "Рік" : `${days} днів`}
            </button>
          ))}
        </div>
        <label className="reports__date">
          <span className="muted">з</span>
          <input className="input" type="date" value={dateFrom} max={dateTo}
                 onChange={(e) => e.target.value && update({ from: e.target.value })} />
        </label>
        <label className="reports__date">
          <span className="muted">по</span>
          <input className="input" type="date" value={dateTo} min={dateFrom}
                 onChange={(e) => e.target.value && update({ to: e.target.value })} />
        </label>
      </div>

      {report.isError && <StateMessage title="Не вдалося побудувати звіт">Перевірте період (до 366 днів).</StateMessage>}
      {report.data && <ReportView report={report.data} stale={report.isPlaceholderData} />}
    </div>
  );
}

function ReportView({ report, stale }: { report: Report; stale: boolean }) {
  return (
    <div className={`reports${stale ? " reports--stale" : ""}`}>
      <div className="reports__metrics">
        {report.metrics.map((metric) => (
          <div key={metric.key} className="reports__metric">
            <span className="muted">{metric.label}</span>
            <strong>{formatValue(metric.value, metric.format)}</strong>
          </div>
        ))}
      </div>

      <div className="reports__charts">
        {report.charts.map((chart) => (
          <figure key={chart.key} className={`reports__chart reports__chart--${chart.kind}`}>
            <figcaption className="reports__chart-title">{chart.title}</figcaption>
            {chart.data.length === 0 || chart.data.every((row) => chart.series.every((s) => !row[s.key])) ? (
              <p className="muted reports__empty">Немає даних за період</p>
            ) : (
              <ChartView chart={chart} />
            )}
          </figure>
        ))}
      </div>

      {report.table && (
        <section>
          <div className="admin__toolbar">
            <h3>{report.table.title}</h3>
            <button className="button button--ghost button--small" onClick={() => downloadCsv(report)}>
              Завантажити CSV
            </button>
          </div>
          {report.table.rows.length === 0 ? (
            <p className="muted">Немає даних за період.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  {report.table.columns.map((c) => (
                    <th key={c.key} className={c.format === "text" ? undefined : "table__number"}>{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.table.rows.map((row, i) => (
                  <tr key={i}>
                    {report.table!.columns.map((c) => (
                      <td key={c.key} className={c.format === "text" ? undefined : "table__number"}>
                        {formatValue(row[c.key], c.format)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {report.notes.length > 0 && (
        <ul className="reports__notes muted">{report.notes.map((note) => <li key={note}>{note}</li>)}</ul>
      )}
      <p className="muted reports__generated">
        Період: {formatDay(report.period.start)} — {formatDay(report.period.end)} · сформовано{" "}
        {new Date(report.generated_at).toLocaleString("uk-UA")}
      </p>
    </div>
  );
}

function ChartView({ chart }: { chart: ReportChart }) {
  const legend = chart.series.length > 1 ? <Legend wrapperStyle={{ fontSize: 13 }} formatter={legendText} /> : null;
  const valueFormat: ValueFormat = chart.series[0].label.includes("грн") ? "money" : "number";
  const wholeNumbers = chart.data.every((row) => chart.series.every((s) => Number.isInteger(row[s.key])));
  const tooltip = (
    <Tooltip {...TOOLTIP} labelFormatter={(label) => formatDay(label as ReportCell)}
             formatter={(value) => formatValue(Number(value), valueFormat)} />
  );

  if (chart.kind === "pie") {
    const series = chart.series[0];
    return (
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={chart.data} dataKey={series.key} nameKey={chart.x_key} innerRadius="55%" outerRadius="80%"
               paddingAngle={chart.data.length > 1 ? 2 : 0} stroke="var(--surface)"
               strokeWidth={chart.data.length > 1 ? 2 : 0} isAnimationActive={false}
               label={({ name, percent, x, y, textAnchor }) => (
                 <text x={x} y={y} textAnchor={textAnchor} dominantBaseline="central" fill="var(--text)" fontSize={13}>
                   {`${name}: ${Math.round((percent ?? 0) * 100)}%`}
                 </text>
               )}>
            {chart.data.map((_, i) => <Cell key={i} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />)}
          </Pie>
          <Tooltip {...TOOLTIP} formatter={(value) => formatValue(Number(value), valueFormat)} />
          <Legend wrapperStyle={{ fontSize: 13 }} formatter={legendText} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chart.kind === "line") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chart.data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={chart.x_key} {...AXIS} tickFormatter={formatDay} minTickGap={16} />
          <YAxis {...AXIS} allowDecimals={!wholeNumbers} />
          {tooltip}
          {legend}
          {chart.series.map((s, i) => (
            <Line key={s.key} dataKey={s.key} name={s.label} stroke={SERIES_COLORS[i]} strokeWidth={2}
                  dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  const horizontal = chart.kind === "hbar";
  const height = horizontal ? Math.max(180, chart.data.length * 26 * chart.series.length + 60) : 260;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chart.data} layout={horizontal ? "vertical" : "horizontal"} barGap={2}
                margin={{ top: 8, right: 16, left: horizontal ? 0 : -12, bottom: 0 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3"
                       vertical={horizontal} horizontal={!horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" {...AXIS} allowDecimals={!wholeNumbers} />
            <YAxis type="category" dataKey={chart.x_key} {...AXIS} width={150}
                   tickFormatter={(v: string) => (v.length > 22 ? `${v.slice(0, 21)}…` : v)} />
          </>
        ) : (
          <>
            <XAxis dataKey={chart.x_key} {...AXIS} tickFormatter={formatDay} minTickGap={8} />
            <YAxis {...AXIS} allowDecimals={!wholeNumbers} />
          </>
        )}
        {tooltip}
        {legend}
        {chart.series.map((s, i) => (
          <Bar key={s.key} dataKey={s.key} name={s.label} fill={SERIES_COLORS[i]} maxBarSize={28}
               radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} isAnimationActive={false} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function downloadCsv(report: Report) {
  const table = report.table!;
  const escape = (value: ReportCell) => `"${String(value).replaceAll('"', '""')}"`;
  const lines = [
    table.columns.map((c) => escape(c.label)).join(";"),
    ...table.rows.map((row) => table.columns.map((c) => escape(row[c.key] ?? "")).join(";")),
  ];
  // BOM so Excel opens Cyrillic correctly.
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${report.code}_${report.period.start}_${report.period.end}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}
