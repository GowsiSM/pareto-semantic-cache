import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ExperimentResults } from "../api/types";
import { SYSTEM_LABELS, SYSTEM_ORDER } from "./ResultsTable";

interface MetricChartRow {
  metric: string;
  GPTCache: number;
  SCALM: number;
  Pareto: number;
}

const BAR_COLORS = {
  GPTCache: "#000000",
  SCALM: "#6b6b6b",
  Pareto: "#b5b5b5",
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

export function ResultsCharts({ results }: { results: ExperimentResults }) {
  const rows = buildRows(results);

  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={rows} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis dataKey="metric" stroke="#000" tick={{ fontSize: 12 }} />
          <YAxis stroke="#000" tick={{ fontSize: 12 }} unit="%" />
          <Tooltip
            contentStyle={{ border: "1px solid #000", borderRadius: 0 }}
            formatter={(value) => `${value}%`}
          />
          <Legend />
          {SYSTEM_ORDER.map((id) => (
            <Bar
              key={id}
              dataKey={SYSTEM_LABELS[id]}
              fill={BAR_COLORS[SYSTEM_LABELS[id] as keyof typeof BAR_COLORS]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
