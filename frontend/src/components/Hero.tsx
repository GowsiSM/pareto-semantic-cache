export function Hero() {
  return (
    <section id="top" className="hero">
      <div className="hero-inner">
        <div className="eyebrow">Final-year project · semantic caching research</div>
        <h1>
          SemantiCache
          <span className="hero-sub">SCALM vs. Pareto-based cache admission</span>
        </h1>
        <p className="hero-lede">
          A live comparison of three semantic cache admission strategies —
          <strong> GPTCache</strong> (flat, unconditional admission),{" "}
          <strong>SCALM</strong> (single-objective, token-saving-ratio ranked), and{" "}
          <strong>Pareto</strong> (two-objective: token savings vs. query volatility).
          Every result below is produced by running the actual backend
          implementation, not simulated in this UI.
        </p>
        <div className="hero-actions">
          <a href="#run-experiment" className="btn btn-primary">
            Run an experiment →
          </a>
          <a href="#architecture" className="btn btn-ghost">
            See how it works
          </a>
        </div>
      </div>
    </section>
  );
}
