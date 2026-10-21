import { useState } from "react";
import type {
  DatasetOption,
  EmbeddingOption,
  ExperimentRequest,
  TraceExperimentRequest,
} from "../api/types";

interface RunExperimentPanelProps {
  onRun: (request: ExperimentRequest) => void;
  isLoading: boolean;
  onTrace?: (request: TraceExperimentRequest) => void;
  isTraceLoading?: boolean;
}

const DEFAULTS: ExperimentRequest = {
  dataset: "synthetic",
  n_queries: 300,
  capacity: 20,
  similarity_threshold: 0.6,
  warmup_count: 100,
  embedding: "mock",
  seed: 42,
};

export function RunExperimentPanel({
  onRun,
  isLoading,
  onTrace,
  isTraceLoading = false,
}: RunExperimentPanelProps) {
  const [form, setForm] = useState<ExperimentRequest>(DEFAULTS);
  const [traceIndex, setTraceIndex] = useState(25);
  const [traceQuery, setTraceQuery] = useState("");
  const [traceAnswer, setTraceAnswer] = useState("");

  const isMoss = form.dataset === "moss";
  const replayCount = Math.max(0, form.n_queries - form.warmup_count);
  const selectedTraceIndex = Math.min(traceIndex, Math.max(0, replayCount - 1));
  const hasCustomQuery = traceQuery.trim().length > 0;
  const hasCustomAnswer = traceAnswer.trim().length > 0;
  const incompleteCustomTrace = hasCustomQuery !== hasCustomAnswer;

  function update<K extends keyof ExperimentRequest>(key: K, value: ExperimentRequest[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleDatasetChange(dataset: DatasetOption) {
    // MOSS runs use the real embedding model and its typical threshold;
    // synthetic runs use the mock embedder, which needs a lower
    // threshold since it only captures lexical overlap.
    setForm((prev) => ({
      ...prev,
      dataset,
      embedding: dataset === "moss" ? "sentence-transformer" : "mock",
      similarity_threshold: dataset === "moss" ? 0.9 : 0.6,
    }));
  }

  return (
    <form
      className="experiment-form"
      onSubmit={(e) => {
        e.preventDefault();
        onRun(form);
      }}
    >
      <div className="form-grid">
        <fieldset className="form-field dataset-field">
          <span>Dataset</span>
          <div className="dataset-options" role="radiogroup" aria-label="Dataset">
            <button
              type="button"
              className={`dataset-option ${form.dataset === "synthetic" ? "is-selected" : ""}`}
              onClick={() => handleDatasetChange("synthetic")}
              aria-pressed={form.dataset === "synthetic"}
            >
              <strong>Synthetic</strong>
              <small>offline / mock</small>
            </button>
            <button
              type="button"
              className={`dataset-option ${form.dataset === "moss" ? "is-selected" : ""}`}
              onClick={() => handleDatasetChange("moss")}
              aria-pressed={form.dataset === "moss"}
            >
              <strong>MOSS</strong>
              <small>real data / embeddings</small>
            </button>
          </div>
        </fieldset>

        <label className="form-field">
          <span>Number of queries</span>
          <input
            type="number"
            min={10}
            max={20000}
            value={form.n_queries}
            onChange={(e) => update("n_queries", Number(e.target.value))}
          />
        </label>

        <label className="form-field">
          <span>Cache capacity</span>
          <input
            type="number"
            min={1}
            max={2000}
            value={form.capacity}
            onChange={(e) => update("capacity", Number(e.target.value))}
          />
        </label>

        <label className="form-field">
          <span>Warmup count</span>
          <input
            type="number"
            min={0}
            max={form.n_queries}
            value={form.warmup_count}
            onChange={(e) => update("warmup_count", Number(e.target.value))}
          />
        </label>

        <label className="form-field">
          <span>Similarity threshold</span>
          <input
            type="number"
            step={0.01}
            min={0}
            max={1}
            value={form.similarity_threshold}
            onChange={(e) => update("similarity_threshold", Number(e.target.value))}
          />
        </label>

        <label className="form-field">
          <span>Embedding provider</span>
          <select
            value={form.embedding}
            onChange={(e) => update("embedding", e.target.value as EmbeddingOption)}
            disabled={isMoss}
            title={isMoss ? "MOSS runs require real embeddings" : undefined}
          >
            <option value="mock">Mock (offline)</option>
            <option value="sentence-transformer">SentenceTransformer (real)</option>
          </select>
        </label>

        <label className="form-field">
          <span>Random seed</span>
          <input
            type="number"
            value={form.seed ?? 42}
            onChange={(e) => update("seed", Number(e.target.value))}
          />
        </label>
      </div>

      {isMoss && (
        <p className="form-note">
          MOSS runs call the real embedding model on the backend and may take
          noticeably longer than the synthetic run.
        </p>
      )}

      <div className="experiment-actions">
        <button type="submit" className="btn btn-primary btn-with-spinner" disabled={isLoading || isTraceLoading}>
          {isLoading && <span className="spinner spinner-inverse" aria-hidden="true" />}
          {isLoading ? "Running…" : "Run measured comparison"}
        </button>
        {onTrace && (
          <div className="trace-action">
            <label className="form-field trace-index-field">
              <span>Replay event after warmup (0-based)</span>
              <input
                type="number"
                min={0}
                max={Math.max(0, replayCount - 1)}
                value={selectedTraceIndex}
                onChange={(event) => setTraceIndex(Number(event.target.value))}
                disabled={isLoading || isTraceLoading || replayCount === 0}
              />
            </label>
            <button
              type="button"
              className="btn btn-secondary btn-with-spinner"
              disabled={isLoading || isTraceLoading || replayCount === 0 || incompleteCustomTrace}
              onClick={() =>
                onTrace({
                  ...form,
                  trace_index: selectedTraceIndex,
                  ...(hasCustomQuery
                    ? { query_text: traceQuery.trim(), answer_text: traceAnswer.trim() }
                    : {}),
                })
              }
            >
              {isTraceLoading && <span className="spinner" aria-hidden="true" />}
              {isTraceLoading ? "Replaying…" : "Trace this workload event"}
            </button>
          </div>
        )}
      </div>
      {onTrace && (
        <>
          <div className="trace-query-fields">
            <label className="form-field">
              <span>Optional query override (blank uses the selected dataset event)</span>
              <textarea
                value={traceQuery}
                maxLength={4000}
                rows={2}
                onChange={(event) => setTraceQuery(event.target.value)}
                disabled={isLoading || isTraceLoading}
              />
            </label>
            <label className="form-field">
              <span>Candidate response (required with a custom query; no LLM call)</span>
              <textarea
                value={traceAnswer}
                maxLength={20000}
                rows={2}
                onChange={(event) => setTraceAnswer(event.target.value)}
                disabled={isLoading || isTraceLoading}
              />
            </label>
          </div>
          {incompleteCustomTrace && (
            <p className="form-validation" role="alert">
              Enter both a custom query and candidate response, or leave both blank to use the dataset event.
            </p>
          )}
          <p className="form-note">
            The trace replays the selected dataset history through the actual
            SCALM and SPARC caches. On a miss, it uses the dataset response or
            your supplied response; it never calls an LLM.
          </p>
        </>
      )}
    </form>
  );
}
