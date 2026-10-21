// ─── ExperimentSection.jsx ───────────────────────────────────────────────────
// Self-contained section that owns the backend experiment state and renders:
//   RunExperimentPanel → StatusBanner → ResultsTable → ResultsCharts → ConclusionSection
//
// All metrics shown here come from the real backend (POST /api/experiments/run).
// Nothing here is simulated.

import { useState } from "react";
import { useExperiment } from "../hooks/useExperiment";
import { RunExperimentPanel } from "./RunExperimentPanel";
import { StatusBanner } from "./StatusBanner";
import { ResultsTable } from "./ResultsTable";
import { ResultsCharts } from "./ResultsCharts";
import { ConclusionSection } from "./ConclusionSection";

// Verified real-data reference numbers from PARETO_AUDIT.md §5b
// (MOSS, 2000 queries, real SentenceTransformer embeddings, capacity=100, threshold=0.90)
const REFERENCE_RESULTS = {
  gptcache: { hit_rate: 0.318, token_saving_rate: 0.086, staleness_rate: 0, false_hit_rate: 0, hits: 636, misses: 1364, total_queries: 2000 },
  scalm:    { hit_rate: 0.185, token_saving_rate: 0.068, staleness_rate: 0, false_hit_rate: 0, hits: 370, misses: 1630, total_queries: 2000 },
  pareto:   { hit_rate: 0.235, token_saving_rate: 0.069, staleness_rate: 0, false_hit_rate: 0, hits: 470, misses: 1530, total_queries: 2000 },
};

const REFERENCE_META = {
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2",
  duration_ms: null,
  dataset_size: 2000,
};

export function ExperimentSection({ theme }) {
  const experiment = useExperiment();
  const [showReference, setShowReference] = useState(false);

  const activeResults = experiment.data?.systems ?? (showReference ? REFERENCE_RESULTS : null);
  const activeMeta    = experiment.data?.meta    ?? (showReference ? REFERENCE_META    : null);
  const isReference   = !experiment.data && showReference;

  return (
    <div className="experiment-section">
      {/* Config form */}
      <RunExperimentPanel
        onRun={experiment.run}
        isLoading={experiment.status === "loading"}
      />

      {/* Status */}
      <div style={{ marginTop: 20 }}>
        <StatusBanner
          status={experiment.status}
          error={experiment.error}
          errorDetail={experiment.errorDetail}
        />
      </div>

      {/* Reference data toggle (when no live results yet) */}
      {experiment.status === "idle" && (
        <div style={{ marginTop: 12 }}>
          <button
            className="btn btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => setShowReference((v) => !v)}
          >
            {showReference ? "Hide reference results" : "Show verified reference results (MOSS, real embeddings)"}
          </button>
        </div>
      )}

      {/* Results */}
      {activeResults && (
        <div style={{ marginTop: 24 }}>
          {/* Label: measured vs. reference */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Measured comparison</h3>
            {isReference ? (
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  background: "#fef3c7",
                  color: "#92400e",
                  padding: "2px 8px",
                  borderRadius: 4,
                }}
              >
                Reference (PARETO_AUDIT §5b — not live)
              </span>
            ) : (
              <span className="measured-badge">Measured by backend</span>
            )}
          </div>

          <ResultsTable results={activeResults} />

          <div style={{ marginTop: 24 }}>
            <ResultsCharts results={activeResults} theme={theme} />
          </div>

          {activeMeta && (
            <div className="experiment-meta">
              {activeMeta.embedding_model}
              {" · "}
              {activeMeta.dataset_size} queries
              {activeMeta.duration_ms ? ` · ${activeMeta.duration_ms}ms` : ""}
              {isReference && " · PARETO_AUDIT.md §5b"}
            </div>
          )}

          <div style={{ marginTop: 24 }}>
            <ConclusionSection results={activeResults} />
          </div>
        </div>
      )}
    </div>
  );
}
