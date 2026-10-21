import type { DecisionTraceResponse, SystemDecisionTrace } from "../api/types";
import { ParetoTradeoffPlot } from "./ParetoTradeoffPlot";

function percent(value: number | null): string {
  return value === null ? "No cached candidate" : `${(value * 100).toFixed(1)}%`;
}

function LookupPanel({
  label,
  trace,
  capacity,
}: {
  label: string;
  trace: SystemDecisionTrace;
  capacity: number;
}) {
  return (
    <article className={`decision-panel ${trace.lookup.hit ? "is-hit" : "is-miss"}`}>
      <div className="decision-panel-heading">
        <h3>{label}</h3>
        <span className={`decision-pill ${trace.lookup.hit ? "hit" : "miss"}`}>
          {trace.lookup.hit ? "CACHE HIT" : "CACHE MISS"}
        </span>
      </div>
      <dl className="decision-facts">
        <div>
          <dt>Nearest cached query</dt>
          <dd>{trace.lookup.nearest_query ?? "Cache is empty"}</dd>
        </div>
        <div>
          <dt>Similarity / threshold</dt>
          <dd>{percent(trace.lookup.similarity)} / {(trace.lookup.threshold * 100).toFixed(1)}%</dd>
        </div>
        <div>
          <dt>Admission after miss</dt>
          <dd>
            {trace.admission.status === "not_evaluated"
              ? "Not evaluated (hit)"
              : `${trace.admission.status.toUpperCase()}${trace.admission.rank ? ` · ${trace.admission.rank} rank` : ""}`}
          </dd>
        </div>
        <div>
          <dt>Reason</dt>
          <dd>{trace.admission.reason}</dd>
        </div>
        <div>
          <dt>Cache before event</dt>
          <dd>
            {trace.cache_before_size} / {capacity}
            {trace.cache_was_full ? " · full" : " · not full"}
          </dd>
        </div>
        <div>
          <dt>Evicted entries</dt>
          <dd>
            {trace.evicted.length
              ? trace.evicted.join("; ")
              : trace.admission.status === "rejected"
                ? "None · rejected candidates do not evict"
                : "None"}
          </dd>
        </div>
        {trace.eviction_reason && (
          <div>
            <dt>Eviction rule</dt>
            <dd>{trace.eviction_reason}</dd>
          </div>
        )}
      </dl>
    </article>
  );
}

function CacheSnapshot({
  label,
  trace,
  capacity,
}: {
  label: string;
  trace: SystemDecisionTrace;
  capacity: number;
}) {
  return (
    <section className="cache-snapshot" aria-label={`${label} cache state after replay`}>
      <div className="snapshot-heading">
        <div>
          <span className="eyebrow">{label}</span>
          <h3>Cache after event</h3>
        </div>
        <strong>{trace.cache_size} / {capacity}</strong>
      </div>
      <ol className="cache-entry-list">
        {trace.cache.map((entry) => (
          <li key={entry.id}>
            <span className="cache-query">{entry.query}</span>
            <span>Retained · {entry.token_saving_proxy} token proxy · risk {entry.volatility.toFixed(2)}</span>
          </li>
        ))}
      </ol>
      {trace.cache.length === 0 && <p className="empty-state">No entries retained.</p>}
    </section>
  );
}

export function DecisionJourney({ data }: { data: DecisionTraceResponse }) {
  return (
    <div className="decision-journey">
      <header className="journey-query">
        <div>
          <span className="eyebrow">
            {data.query_source === "user input"
              ? `Custom query · replay position ${data.replay_index + 1}`
              : `Workload event ${data.replay_index + 1} · dataset row ${data.workload_index + 1}`}
          </span>
          <h2>{data.query}</h2>
        </div>
        <p>
          Recorded response: {data.candidate_answer_tokens} answer tokens.
          {` ${data.answer_source}`}
        </p>
      </header>

      <div className="journey-stages" aria-label="Query journey stages">
        <span>Query</span><i aria-hidden="true">→</i>
        <span>Similarity search</span><i aria-hidden="true">→</i>
        <span>Threshold decision</span><i aria-hidden="true">→</i>
        <span>Admission / cache state</span>
      </div>

      <div className="decision-grid">
        <LookupPanel label="SCALM · fixed threshold" trace={data.systems.scalm} capacity={data.request.capacity} />
        <LookupPanel label="SPARC · adaptive threshold" trace={data.systems.pareto} capacity={data.request.capacity} />
      </div>

      {data.systems.pareto.volatility !== undefined && (
        <aside className="risk-callout" id="risk-assessment">
          <strong>SPARC risk estimate</strong>
          <span>
            {data.systems.pareto.volatility_label} · score{" "}
            {data.systems.pareto.volatility.toFixed(2)} · domain{" "}
            {data.systems.pareto.domain}
          </span>
          <p>
            This project’s keyword heuristic adjusts the lookup threshold; it
            is not a confidence score or ground-truth freshness measurement.
          </p>
        </aside>
      )}

      <section className="journey-plot-section" id="pareto-tradeoff" aria-labelledby="tradeoff-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Candidate trade-off · actual replay values</span>
            <h2 id="tradeoff-title">The Pareto decision</h2>
          </div>
        </div>
        <ParetoTradeoffPlot trace={data.systems.pareto} />
      </section>

      <section className="journey-cache-section" id="cache-state">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Membership after this event</span>
            <h2>Two cache states</h2>
          </div>
        </div>
        <div className="cache-snapshot-grid">
          <CacheSnapshot label="SCALM" trace={data.systems.scalm} capacity={data.request.capacity} />
          <CacheSnapshot label="SPARC" trace={data.systems.pareto} capacity={data.request.capacity} />
        </div>
        <p className="method-note">
          The chart and event labels reproduce the backend’s current policy.
          Its Pareto eviction path computes contributions for a dominated-entry
          subset when one exists; hypervolume contribution is formally defined
          for a frontier, so that particular tie-break still needs independent
          algorithm validation.
        </p>
      </section>
    </div>
  );
}
