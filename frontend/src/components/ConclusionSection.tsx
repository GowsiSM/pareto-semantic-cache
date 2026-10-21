import type { ExperimentResults, CacheSystemId } from "../api/types";
import { SYSTEM_LABELS } from "./ResultsTable";

interface MetricSpec {
  label: string;
  key: keyof ExperimentResults["gptcache"];
  higherIsBetter: boolean;
}

const METRICS: MetricSpec[] = [
  { label: "hit ratio", key: "hit_rate", higherIsBetter: true },
  { label: "token savings", key: "token_saving_rate", higherIsBetter: true },
  { label: "staleness rate", key: "staleness_rate", higherIsBetter: false },
  { label: "false-hit rate", key: "false_hit_rate", higherIsBetter: false },
];

function bestSystemsFor(
  results: ExperimentResults,
  metric: MetricSpec,
  ids: CacheSystemId[],
): CacheSystemId[] {
  const bestValue = ids.reduce((best, id) => {
    const value = results[id][metric.key];
    return metric.higherIsBetter ? Math.max(best, value) : Math.min(best, value);
  }, results[ids[0]][metric.key]);
  return ids.filter((id) => Math.abs(results[id][metric.key] - bestValue) <= 1e-12);
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function ConclusionSection({
  results,
  systems = ["gptcache", "scalm", "pareto"],
}: {
  results: ExperimentResults;
  systems?: CacheSystemId[];
}) {
  const leaders = METRICS.map((metric) => ({
    metric,
    systems: bestSystemsFor(results, metric, systems),
  }));

  const paretoWins = leaders.filter((l) => l.systems.length === 1 && l.systems[0] === "pareto");
  const scalmWins = leaders.filter((l) => l.systems.length === 1 && l.systems[0] === "scalm");
  const gptcacheWins = leaders.filter((l) => l.systems.length === 1 && l.systems[0] === "gptcache");
  const uniqueLeaderCount = gptcacheWins.length + scalmWins.length + paretoWins.length;

  return (
    <div className="conclusion">
      <p>
        This run's results, computed directly from the returned metrics — no
        fixed narrative:
      </p>
      <ul className="conclusion-list">
        {leaders.map(({ metric, systems }) => (
          <li key={metric.label}>
            <strong>{systems.map((id) => SYSTEM_LABELS[id]).join(" and ")}</strong>{" "}
            {systems.length > 1 ? "tied for" : "had"} the best {metric.label} (
            {pct(results[systems[0]][metric.key])}
            {metric.higherIsBetter ? ", highest" : ", lowest"}).
          </li>
        ))}
      </ul>
      <p>
        {uniqueLeaderCount === 0 && "No metric had a unique leader in this run. "}
        {gptcacheWins.length > 0 && (
          <>
            GPTCache's unconditional admission policy tends to lead on raw{" "}
            {gptcacheWins.map((l) => l.metric.label).join(" and ")} in this run,
            since it never rejects a candidate — there is no selection pressure
            working against it on those metrics.{" "}
          </>
        )}
        {paretoWins.length > 0 && (
          <>
            Pareto's two-objective admission led on{" "}
            {paretoWins.map((l) => l.metric.label).join(" and ")}, consistent with
            its more selective, dominance-based admission policy.{" "}
          </>
        )}
        {scalmWins.length > 0 && (
          <>
            SCALM's single-objective ranking led on{" "}
            {scalmWins.map((l) => l.metric.label).join(" and ")} in this run.{" "}
          </>
        )}
      </p>
      <p className="conclusion-note">
        {systems.length === 2
          ? "This is a head-to-head comparison for the selected run; results may change with the workload and configuration."
          : "No system dominates every metric simultaneously in general — that is the expected shape of a genuine multi-objective trade-off, not a ranking to be collapsed into a single winner. Re-run with different parameters (dataset, capacity, similarity threshold) to see how this balance shifts."}
      </p>
    </div>
  );
}
