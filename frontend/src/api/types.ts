/**
 * Types matching the FastAPI contract in backend/api.py.
 * Metric names match validator outputs; trace details come from replaying a
 * selected dataset event through the existing cache classes.
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

export interface TraceExperimentRequest extends ExperimentRequest {
  /** Zero-based index within the replay queries after the warmup phase. */
  trace_index: number;
  /** Optional query override; paired with answer_text for a real admission trace. */
  query_text?: string;
  answer_text?: string;
}

export interface TraceLookup {
  hit: boolean;
  similarity: number | null;
  threshold: number;
  nearest_query: string | null;
  nearest_entry_id: string | null;
}

export type AdmissionStatus = "not_evaluated" | "admitted" | "rejected";

export interface TraceAdmission {
  status: AdmissionStatus;
  reason: string;
  rank?: "high" | "mid" | "low" | null;
  is_frontier?: boolean | null;
  dominated_by?: string[];
}

export interface TraceCacheEntry {
  id: string;
  query: string;
  token_saving_proxy: number;
  volatility: number;
  objective: [number, number];
  hits: number;
}

export interface ParetoPlotPoint extends TraceCacheEntry {
  is_candidate: boolean;
  is_frontier: boolean;
  dominated_by: string[];
  is_in_cache_after: boolean;
}

export interface SystemDecisionTrace {
  lookup: TraceLookup;
  admission: TraceAdmission;
  evicted: string[];
  eviction_reason: string | null;
  cache_before_size: number;
  cache_was_full: boolean;
  cache_size: number;
  cache: TraceCacheEntry[];
  domain?: string;
  volatility_label?: string;
  volatility?: number;
  plot_points?: ParetoPlotPoint[];
}

export interface DecisionTraceResponse {
  request: TraceExperimentRequest;
  dataset_size: number;
  workload_index: number;
  replay_index: number;
  query_source: string;
  query: string;
  candidate_answer_tokens: number;
  answer_source: string;
  systems: {
    scalm: SystemDecisionTrace;
    pareto: SystemDecisionTrace;
  };
}

export interface ApiErrorShape {
  error: string;
  detail?: string;
}
