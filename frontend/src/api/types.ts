/**
 * Types matching the REST API contract this frontend expects from the
 * backend. This API does NOT exist yet in the current backend (which is
 * a set of CLI scripts, not an HTTP server) — see README.md "Backend API
 * Contract" section for the exact endpoints and shapes the backend needs
 * to implement for this frontend to work.
 *
 * Field names deliberately match the real metric names already used by
 * ParetoValidator / SCALMValidator / GPTCache in the Python backend
 * (hit_rate, token_saving_rate, staleness_rate, false_hit_rate), so the
 * backend can return its existing validator.run() dict shapes with
 * minimal translation.
 */

export type CacheSystemId = "gptcache" | "scalm" | "pareto";

export interface SystemMetrics {
  hit_rate: number;
  token_saving_rate: number;
  staleness_rate: number;
  false_hit_rate: number;
  hits: number;
  misses: number;
  total_queries: number;
}

export type ExperimentResults = Record<CacheSystemId, SystemMetrics>;

export type DatasetOption = "synthetic" | "moss";
export type EmbeddingOption = "mock" | "sentence-transformer";

export interface ExperimentRequest {
  dataset: DatasetOption;
  n_queries: number;
  capacity: number;
  similarity_threshold: number;
  warmup_count: number;
  embedding: EmbeddingOption;
  seed?: number;
}

export interface ExperimentResponse {
  request: ExperimentRequest;
  systems: ExperimentResults;
  meta: {
    embedding_model: string;
    duration_ms: number;
    dataset_size: number;
  };
}

export interface ApiErrorShape {
  error: string;
  detail?: string;
}
