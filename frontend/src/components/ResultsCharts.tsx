import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CacheSystemId, ExperimentResults } from "../api/types";
import type { Theme } from "../hooks/useTheme";
import { SYSTEM_LABELS, SYSTEM_ORDER } from "./ResultsTable";

// Consistent per-system colors matching the CSS design tokens.
// These are hard-coded values (same as --pareto-color, --scalm-color, --gptcache-color)
// so they work without CSS variable access inside Recharts SVG.
const SYSTEM_COLORS: Record<string, string> = {
  gptcache: "#475569", // slate-600
  scalm: "#d97706",   // amber-600
  pareto: "#0d9488",  // teal-600 (SPARC)
};

interface MetricChartRow {
  metric: string;
  [key: string]: number | string;
}

function buildRows(results: ExperimentResults, systems: CacheSystemId[]): MetricChartRow[] {
  const metricKeys: { label: string; key: keyof ExperimentResults["gptcache"] }[] = [
    { label: "Hit Ratio", key: "hit_rate" },
    { label: "Token Saving", key: "token_saving_rate" },
    { label: "Staleness", key: "staleness_rate" },
    { label: "False-Hit", key: "false_hit_rate" },
  ];

  return metricKeys.map(({ label, key }) => {
    const row: MetricChartRow = { metric: label };
    for (const id of systems) {
      row[SYSTEM_LABELS[id]] = Number((results[id][key] * 100).toFixed(2));
    }
    return row;
  });
}

export function ResultsCharts({
  results,
  theme,
  systems = SYSTEM_ORDER,
}: {
  results: ExperimentResults;
  theme: Theme;
  systems?: CacheSystemId[];
}) {
  const rows = buildRows(results, systems);
  const axisColor = theme === "dark" ? "#f2f2f2" : "#0f172a";
  const gridColor = theme === "dark" ? "#333333" : "#e2e8f0";
  const tooltipBg = theme === "dark" ? "#1e293b" : "#ffffff";

  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height={380}>
        <BarChart data={rows} margin={{ top: 16, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="metric"
            stroke={axisColor}
            tick={{ fontSize: 12, fill: axisColor }}
          />
          <YAxis
            stroke={axisColor}
            tick={{ fontSize: 12, fill: axisColor }}
            unit="%"
          />
          <Tooltip
            contentStyle={{
              border: `1px solid ${gridColor}`,
              borderRadius: 6,
              background: tooltipBg,
              color: axisColor,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}%`]}
          />
          <Legend
            wrapperStyle={{ color: axisColor, fontSize: 12 }}
          />
          {systems.map((id) => (
            <Bar
              key={id}
              dataKey={SYSTEM_LABELS[id]}
              fill={SYSTEM_COLORS[id]}
              radius={[3, 3, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
