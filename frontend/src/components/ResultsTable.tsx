import type { ExperimentResults, CacheSystemId } from "../api/types";

const SYSTEM_LABELS: Record<CacheSystemId, string> = {
  gptcache: "GPTCache",
  scalm: "SCALM",
  pareto: "Pareto",
};

const SYSTEM_ORDER: CacheSystemId[] = ["gptcache", "scalm", "pareto"];

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function ResultsTable({ results }: { results: ExperimentResults }) {
  return (
    <table className="results-table">
      <thead>
        <tr>
          <th>Metric</th>
          {SYSTEM_ORDER.map((id) => (
            <th key={id}>{SYSTEM_LABELS[id]}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Hit Ratio</td>
          {SYSTEM_ORDER.map((id) => (
            <td key={id}>{pct(results[id].hit_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>Token Saving Ratio</td>
          {SYSTEM_ORDER.map((id) => (
            <td key={id}>{pct(results[id].token_saving_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>Staleness Rate</td>
          {SYSTEM_ORDER.map((id) => (
            <td key={id}>{pct(results[id].staleness_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>False-Hit Rate</td>
          {SYSTEM_ORDER.map((id) => (
            <td key={id}>{pct(results[id].false_hit_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>Hits / Misses</td>
          {SYSTEM_ORDER.map((id) => (
            <td key={id}>
              {results[id].hits} / {results[id].misses}
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

export { SYSTEM_LABELS, SYSTEM_ORDER };
