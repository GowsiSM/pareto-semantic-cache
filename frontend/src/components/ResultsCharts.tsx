import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ExperimentResults } from "../api/types";
import type { Theme } from "../hooks/useTheme";
import { SYSTEM_LABELS, SYSTEM_ORDER } from "./ResultsTable";

interface MetricChartRow {
  metric: string;
  GPTCache: number;
  SCALM: number;
  Pareto: number;
}

// Distinct per-theme palettes: pure black/white extremes would make a
// bar invisible against a same-color background, so light and dark
// modes each get colors with real contrast against their own canvas.
const BAR_COLORS: Record<Theme, { GPTCache: string; SCALM: string; Pareto: string }> = {
  light: { GPTCache: "#0a0a0a", SCALM: "#6b6b6b", Pareto: "#b5b5b5" },
  dark: { GPTCache: "#f2f2f2", SCALM: "#a3a3a3", Pareto: "#5a5a5a" },
};

function buildRows(results: ExperimentResults): MetricChartRow[] {
  const metricKeys: { label: string; key: keyof ExperimentResults["gptcache"] }[] = [
    { label: "Hit Ratio", key: "hit_rate" },
    { label: "Token Saving", key: "token_saving_rate" },
    { label: "Staleness", key: "staleness_rate" },
    { label: "False-Hit", key: "false_hit_rate" },
  ];

  return metricKeys.map(({ label, key }) => ({
    metric: label,
    GPTCache: Number((results.gptcache[key] * 100).toFixed(2)),
    SCALM: Number((results.scalm[key] * 100).toFixed(2)),
    Pareto: Number((results.pareto[key] * 100).toFixed(2)),
  }));
}

export function ResultsCharts({ results, theme }: { results: ExperimentResults; theme: Theme }) {
  const rows = buildRows(results);
  const colors = BAR_COLORS[theme];
  const axisColor = theme === "dark" ? "#f2f2f2" : "#0a0a0a";
  const gridColor = theme === "dark" ? "#333333" : "#e5e5e5";
  const tooltipBg = theme === "dark" ? "#171717" : "#ffffff";

  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={rows} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="metric" stroke={axisColor} tick={{ fontSize: 12, fill: axisColor }} />
          <YAxis stroke={axisColor} tick={{ fontSize: 12, fill: axisColor }} unit="%" />
          <Tooltip
            contentStyle={{
              border: `1px solid ${axisColor}`,
              borderRadius: 0,
              background: tooltipBg,
              color: axisColor,
            }}
            formatter={(value) => `${value}%`}
          />
          <Legend wrapperStyle={{ color: axisColor }} />
          {SYSTEM_ORDER.map((id) => (
            <Bar key={id} dataKey={SYSTEM_LABELS[id]} fill={colors[SYSTEM_LABELS[id] as keyof typeof colors]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
