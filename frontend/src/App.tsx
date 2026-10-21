import { useState } from "react";
import { ConclusionSection } from "./components/ConclusionSection";
import { DecisionJourney } from "./components/DecisionJourney";
import { ResultsCharts } from "./components/ResultsCharts";
import { SYSTEM_ORDER, ResultsTable } from "./components/ResultsTable";
import { RunExperimentPanel } from "./components/RunExperimentPanel";
import { StatusBanner } from "./components/StatusBanner";
import type { CacheSystemId } from "./api/types";
import { useDecisionTrace } from "./hooks/useDecisionTrace";
import { useExperiment } from "./hooks/useExperiment";
import { useTheme } from "./hooks/useTheme";
import "./conference.css";

const PRESENTATION_STAGES = [
  { title: "The problem", target: "research-problem" },
  { title: "A query enters", target: "query-journey" },
  { title: "Baseline decision", target: "query-journey" },
  { title: "Freshness risk", target: "risk-assessment" },
  { title: "Pareto trade-off", target: "pareto-tradeoff" },
  { title: "Cache evolution", target: "cache-state" },
  { title: "Measured comparison", target: "measured-results" },
];

function App() {
  const experiment = useExperiment();
  const trace = useDecisionTrace();
  const { theme, toggleTheme } = useTheme();
  const [conferenceMode, setConferenceMode] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [formRevision, setFormRevision] = useState(0);
  const [showGptCache, setShowGptCache] = useState(false);

  function goToStage(index: number) {
    setActiveStage(index);
    document.getElementById(PRESENTATION_STAGES[index].target)?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  }

  function resetDemo() {
    experiment.reset();
    trace.reset();
    setActiveStage(0);
    setFormRevision((value) => value + 1);
    setShowGptCache(false);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  const latestQuery = trace.data?.query;
  const latestDecision = trace.data?.systems;
  const comparisonSystems: CacheSystemId[] = showGptCache
    ? SYSTEM_ORDER
    : ["scalm", "pareto"];

  return (
    <div className={`conference-app${conferenceMode ? " is-conference" : ""}`} data-theme={theme}>
      <header className="research-header">
        <a className="research-brand" href="#top" aria-label="SPARC research console home">
          <span className="brand-mark">S</span>
          <span>SPARC <small>RESEARCH CONSOLE</small></span>
        </a>
        <div className="header-context">
          <span>ICECCE 2026 · semantic caching</span>
          <span className="header-separator" aria-hidden="true">/</span>
          <span>SCALM baseline vs. Pareto policy</span>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="utility-button"
            aria-pressed={conferenceMode}
            onClick={() => setConferenceMode((value) => !value)}
          >
            {conferenceMode ? "Exit presentation mode" : "Presentation mode"}
          </button>
          <button type="button" className="utility-button" onClick={resetDemo}>
            Reset demo
          </button>
          <button
            type="button"
            className="theme-button"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
          >
            {theme === "light" ? "Dark" : "Light"}
          </button>
        </div>
      </header>

      <div className="live-summary" aria-live="polite">
        <span className="live-summary-label">CURRENT REPLAY</span>
        <strong>{latestQuery ?? "No event traced yet"}</strong>
        {latestDecision ? (
          <span className="live-summary-metrics">
            SCALM {latestDecision.scalm.lookup.hit ? "HIT" : "MISS"} · SPARC{" "}
            {latestDecision.pareto.lookup.hit ? "HIT" : "MISS"} · cache{" "}
            {latestDecision.pareto.cache_size}/{trace.data?.request.capacity}
          </span>
        ) : (
          <span className="live-summary-metrics">Run a real workload trace to populate this view</span>
        )}
      </div>

      <main id="top">
        <section className="intro-section" id="research-problem">
          <div className="intro-copy">
            <span className="eyebrow">A visual laboratory for cache decisions</span>
            <h1>When should an LLM answer be reused?</h1>
            <p>
              Semantic caching can save inference work, but a similar query may
              need a fresher answer. Compare the fixed-threshold SCALM baseline
              with SPARC’s project-proposed Pareto admission policy using the
              same replayed workload.
            </p>
            <div className="intro-principle">
              <span>THE TRADE-OFF</span>
              <strong>More tokens saved is not always a safer cache entry.</strong>
            </div>
          </div>
          <div className="pipeline-visual" aria-label="Query, semantic match, risk, decision, cache state, measured outcome">
            {["Query", "Match", "Risk", "Decision", "Cache", "Evidence"].map((label, index) => (
              <div className="pipeline-step" key={label}>
                <span className="pipeline-number">0{index + 1}</span>
                <strong>{label}</strong>
                {index < 5 && <i aria-hidden="true" />}
              </div>
            ))}
          </div>
        </section>

        <section className="stage-navigator" aria-label="Presentation guide">
          <div className="stage-navigator-heading">
            <span className="eyebrow">10–12 MIN WALKTHROUGH</span>
            <span>Choose a stage to jump to it; all controls remain interactive.</span>
          </div>
          <ol>
            {PRESENTATION_STAGES.map((stage, index) => (
              <li key={stage.title}>
                <button
                  type="button"
                  className={activeStage === index ? "stage-button is-active" : "stage-button"}
                  aria-current={activeStage === index ? "step" : undefined}
                  onClick={() => goToStage(index)}
                >
                  <span>0{index + 1}</span>
                  {stage.title}
                </button>
              </li>
            ))}
          </ol>
          <div className="stage-controls">
            <button
              type="button"
              className="stage-next"
              onClick={() => goToStage(Math.min(activeStage + 1, PRESENTATION_STAGES.length - 1))}
              disabled={activeStage === PRESENTATION_STAGES.length - 1}
            >
              Next stage <span aria-hidden="true">→</span>
            </button>
          </div>
        </section>

        <section className="workspace-section" id="query-journey">
          <div className="section-heading">
            <div>
              <span className="eyebrow">01 / Replay an actual workload event</span>
              <h2>Follow one query through both policies</h2>
              <p>
                The backend replays the selected dataset up to this event, then
                returns the actual nearest match, threshold, admission result,
                eviction, and cache contents.
              </p>
            </div>
            <span className="source-tag">BACKEND TRACE · NO GENERATED DELAYS</span>
          </div>

          <details className="controls-disclosure" open={!conferenceMode}>
            <summary>Workload and replay controls</summary>
            <RunExperimentPanel
              key={formRevision}
              onRun={experiment.run}
              isLoading={experiment.status === "loading"}
              onTrace={trace.run}
              isTraceLoading={trace.status === "loading"}
            />
          </details>

          <div className="status-stack" aria-live="polite">
            {trace.status === "loading" && (
              <div className="status-banner status-loading" role="status">
                Replaying workload events through the backend cache implementations…
              </div>
            )}
            {trace.status === "error" && (
              <div className="status-banner status-error" role="alert">
                <strong>{trace.error}</strong>
                {trace.errorDetail && <p className="status-detail">{trace.errorDetail}</p>}
              </div>
            )}
            {trace.status === "success" && (
              <div className="status-banner status-complete" role="status">
                Replay complete · decision details below are from the backend.
              </div>
            )}
          </div>

          {trace.data && (
            <DecisionJourney data={trace.data} />
          )}
          {!trace.data && (
            <div className="empty-workspace">
              <span className="empty-symbol" aria-hidden="true">↘</span>
              <div>
                <strong>{trace.status === "error" ? "Trace unavailable" : "No replay event loaded"}</strong>
                <p>
                  {trace.status === "error"
                    ? "Resolve the backend error above and retry; no example result is substituted."
                    : "Choose a dataset and trace event above, then follow the real cache decision here."}
                </p>
              </div>
            </div>
          )}
          {!trace.data && (
            <div className="pending-visuals">
              <aside className="risk-callout" id="risk-assessment">
                <strong>Freshness-risk estimate</strong>
                <span>Waiting for a query trace</span>
                <p>The backend keyword heuristic score appears here; it is not a ground-truth freshness measurement.</p>
              </aside>
              <section className="empty-stage" id="pareto-tradeoff">
                <span className="eyebrow">Pareto trade-off</span>
                <h3>Actual objective values appear after a trace</h3>
                <p>No sample points or frontier membership are substituted.</p>
              </section>
              <section className="empty-stage" id="cache-state">
                <span className="eyebrow">Cache state</span>
                <h3>Admission and eviction events appear after a trace</h3>
                <p>Cache entries and occupancy are read from the backend response.</p>
              </section>
            </div>
          )}
        </section>

        <section className="policy-section" aria-labelledby="policy-title">
          <div className="section-heading">
            <div>
              <span className="eyebrow">02 / Policy contrast</span>
              <h2 id="policy-title">Same cache problem, different admission logic</h2>
            </div>
            <span className="source-tag">PROJECT IMPLEMENTATION</span>
          </div>
          <div className="policy-comparison">
            <article className="policy-column scalm-policy">
              <span className="policy-index">BASELINE</span>
              <h3>SCALM</h3>
              <p>Similarity lookup uses a fixed threshold. On a miss, clustered pattern rank guides admission; rank-seeded LFU chooses an eviction victim.</p>
              <div className="policy-rule"><span>LOOKUP</span><strong>Similarity ≥ configured τ</strong></div>
              <div className="policy-rule"><span>ADMISSION</span><strong>Low rank allowed while not full; Mid/High when full</strong></div>
            </article>
            <article className="policy-column sparc-policy">
              <span className="policy-index">PROPOSED EXTENSION</span>
              <h3>SPARC / Pareto</h3>
              <p>Adaptive threshold for lookup; on a full cache, compare token-saving proxy and volatility without collapsing them into one weighted score.</p>
              <div className="policy-rule"><span>OBJECTIVES</span><strong>Maximize token proxy · minimize volatility</strong></div>
              <div className="policy-rule"><span>ADMISSION</span><strong>Non-dominated when full; otherwise unconditional</strong></div>
            </article>
          </div>
          <p className="method-note">
            The adaptive threshold, volatility signal, and Pareto rule are this
            project’s extension; they should not be attributed to the SCALM paper.
          </p>
        </section>

        <section className="workspace-section experiment-section" id="measured-results">
          <div className="section-heading">
            <div>
              <span className="eyebrow">03 / Experimental evidence</span>
              <h2>Compare measured outcomes</h2>
              <p>
                    The primary comparison is SCALM versus SPARC on the same
                    configured workload. GPTCache remains available as a separate
                    reference baseline.
              </p>
            </div>
            <span className="source-tag">POST /api/experiments/run</span>
          </div>

          <div className="experiment-run-row">
            <span>
              {experiment.status === "success" && experiment.data
                ? `${experiment.data.request.dataset.toUpperCase()} · ${experiment.data.meta.dataset_size} queries · ${experiment.data.meta.embedding_model}`
                : "Configure and run the measured comparison in the controls above."}
            </span>
            <StatusBanner
              status={experiment.status}
              error={experiment.error}
              errorDetail={experiment.errorDetail}
            />
          </div>

          {experiment.status === "loading" && (
            <p className="status-note">Waiting for the backend experiment to complete. No placeholder results are shown.</p>
          )}
          {experiment.status === "success" && experiment.data && (
            <div className="measured-results">
              <label className="baseline-toggle">
                <input
                  type="checkbox"
                  checked={showGptCache}
                  onChange={(event) => setShowGptCache(event.target.checked)}
                />
                <span>Show GPTCache reference baseline</span>
              </label>
              {showGptCache && (
                <aside className="baseline-context">
                  GPTCache uses unconditional admission. The paper describes
                  it as a separate reference rather than a direct comparison
                  with the staged SCALM–SPARC validation; interpret these
                  results accordingly.
                </aside>
              )}
              <div className="result-meta">
                <span>Embedding: <strong>{experiment.data.meta.embedding_model}</strong></span>
                <span>Dataset rows: <strong>{experiment.data.meta.dataset_size}</strong></span>
                <span>Backend run time: <strong>{experiment.data.meta.duration_ms.toFixed(0)} ms</strong></span>
                <span>Replay queries: <strong>{experiment.data.systems.pareto.total_queries}</strong></span>
              </div>
              <ResultsTable
                results={experiment.data.systems}
                systems={comparisonSystems}
              />
              <ResultsCharts
                results={experiment.data.systems}
                theme={theme}
                systems={comparisonSystems}
              />
              <div className="interpretation">
                <h3>Read the trade-offs, not a single winner</h3>
                <ConclusionSection
                  results={experiment.data.systems}
                  systems={comparisonSystems}
                />
              </div>
              <p className="method-note">
                Staleness and false-hit values follow the backend validator’s
                definitions. The current API does not provide per-query latency
                or ground-truth answer freshness; a low observed rate in one
                replay does not establish general freshness.
              </p>
            </div>
          )}
          {experiment.status === "idle" && (
            <div className="empty-results">
              Experimental results appear here only after a successful backend run.
            </div>
          )}
        </section>

        <footer className="research-footer">
          <span>SPARC · Pareto-based semantic cache admission</span>
          <span>Replay and aggregate results are backend-generated; no simulated metrics.</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
