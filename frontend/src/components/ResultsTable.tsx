import type { ExperimentResults, CacheSystemId } from "../api/types";

const SYSTEM_LABELS: Record<CacheSystemId, string> = {
  gptcache: "GPTCache (baseline)",
  scalm: "SCALM (baseline)",
  pareto: "SPARC / Pareto",
};

const SYSTEM_ORDER: CacheSystemId[] = ["gptcache", "scalm", "pareto"];

const SYSTEM_COL_CLASS: Record<CacheSystemId, string> = {
  gptcache: "gptcache-col",
  scalm: "scalm-col",
  pareto: "pareto-col",
};

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function ResultsTable({
  results,
  systems = SYSTEM_ORDER,
}: {
  results: ExperimentResults;
  systems?: CacheSystemId[];
}) {
  return (
    <table className="results-table">
      <thead>
        <tr>
          <th>Metric</th>
          {systems.map((id) => (
            <th key={id} className={SYSTEM_COL_CLASS[id]}>{SYSTEM_LABELS[id]}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Hit Ratio ↑</td>
          {systems.map((id) => (
            <td key={id} className={SYSTEM_COL_CLASS[id]}>{pct(results[id].hit_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>Token Saving Ratio ↑</td>
          {systems.map((id) => (
            <td key={id} className={SYSTEM_COL_CLASS[id]}>{pct(results[id].token_saving_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>Staleness Rate ↓</td>
          {systems.map((id) => (
            <td key={id}>{pct(results[id].staleness_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>False-Hit Rate ↓</td>
          {systems.map((id) => (
            <td key={id}>{pct(results[id].false_hit_rate)}</td>
          ))}
        </tr>
        <tr>
          <td>Hits / Misses</td>
          {systems.map((id) => (
            <td key={id} className={SYSTEM_COL_CLASS[id]}>
              {results[id].hits} / {results[id].misses}
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

export { SYSTEM_LABELS, SYSTEM_ORDER, SYSTEM_COL_CLASS };
