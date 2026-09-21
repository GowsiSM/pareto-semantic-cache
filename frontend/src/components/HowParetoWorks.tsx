export function HowParetoWorks() {
  return (
    <div className="how-pareto">
      <div className="how-pareto-row">
        <div className="how-pareto-card">
          <div className="how-pareto-label">Objective 1</div>
          <div className="how-pareto-value">Token-Saving Proxy</div>
          <p>
            Derived from a candidate entry's own token count (query + response),
            weighted by observed reuse frequency. Higher is better — this is
            maximized.
          </p>
        </div>
        <div className="how-pareto-plus" aria-hidden="true">
          +
        </div>
        <div className="how-pareto-card">
          <div className="how-pareto-label">Objective 2</div>
          <div className="how-pareto-value">Query Volatility</div>
          <p>
            A lightweight classifier scores each query STABLE, TEMPORAL, or
            PERSONAL. Lower is better — this is minimized.
          </p>
        </div>
      </div>

      <div className="how-pareto-arrow" aria-hidden="true">
        ↓
      </div>

      <div className="how-pareto-single">
        <div className="how-pareto-label">Pareto Dominance</div>
        <p>
          A candidate is admitted only if no existing cache entry is at least as
          good on <em>both</em> objectives and strictly better on one. No fixed
          weight is assigned between token savings and volatility — trade-off
          points are preserved rather than collapsed into a single score.
        </p>
      </div>

      <div className="how-pareto-arrow" aria-hidden="true">
        ↓
      </div>

      <div className="how-pareto-single">
        <div className="how-pareto-label">Capacity Management</div>
        <p>
          When the non-dominated set exceeds cache capacity, the entry with the
          smallest hypervolume contribution — the least unique value in
          objective space — is evicted first.
        </p>
      </div>
    </div>
  );
}
