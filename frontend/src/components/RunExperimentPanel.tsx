import { useState } from "react";
import type { DatasetOption, EmbeddingOption, ExperimentRequest } from "../api/types";

interface RunExperimentPanelProps {
  onRun: (request: ExperimentRequest) => void;
  isLoading: boolean;
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

export function RunExperimentPanel({ onRun, isLoading }: RunExperimentPanelProps) {
  const [form, setForm] = useState<ExperimentRequest>(DEFAULTS);

  const isMoss = form.dataset === "moss";

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
        <label className="form-field">
          <span>Dataset</span>
          <select
            value={form.dataset}
            onChange={(e) => handleDatasetChange(e.target.value as DatasetOption)}
          >
            <option value="synthetic">Synthetic (offline, mock embeddings)</option>
            <option value="moss">MOSS (real data, real embeddings)</option>
          </select>
        </label>

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

      <button type="submit" className="btn btn-primary btn-with-spinner" disabled={isLoading}>
        {isLoading && <span className="spinner spinner-inverse" aria-hidden="true" />}
        {isLoading ? "Running…" : "Run experiment"}
      </button>
    </form>
  );
}
