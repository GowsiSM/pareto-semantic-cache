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

function bestSystemFor(results: ExperimentResults, metric: MetricSpec): CacheSystemId {
  const ids: CacheSystemId[] = ["gptcache", "scalm", "pareto"];
  return ids.reduce((best, id) => {
    const better = metric.higherIsBetter
      ? results[id][metric.key] > results[best][metric.key]
      : results[id][metric.key] < results[best][metric.key];
    return better ? id : best;
  }, ids[0]);
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function ConclusionSection({ results }: { results: ExperimentResults }) {
  const leaders = METRICS.map((metric) => ({
    metric,
    winner: bestSystemFor(results, metric),
  }));

  const paretoWins = leaders.filter((l) => l.winner === "pareto");
  const scalmWins = leaders.filter((l) => l.winner === "scalm");
  const gptcacheWins = leaders.filter((l) => l.winner === "gptcache");

  return (
    <div className="conclusion">
      <p>
        This run's results, computed directly from the returned metrics — no
        fixed narrative:
      </p>
      <ul className="conclusion-list">
        {leaders.map(({ metric, winner }) => (
          <li key={metric.label}>
            <strong>{SYSTEM_LABELS[winner]}</strong> had the best {metric.label} (
            {pct(results[winner][metric.key])}
            {metric.higherIsBetter ? ", highest" : ", lowest"}).
          </li>
        ))}
      </ul>
      <p>
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
        No system dominates every metric simultaneously in general — that is
        the expected shape of a genuine multi-objective trade-off, not a
        ranking to be collapsed into a single winner. Re-run with different
        parameters (dataset, capacity, similarity threshold) to see how this
        balance shifts.
      </p>
    </div>
  );
}
