import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DecisionTraceResponse, ParetoPlotPoint, SystemDecisionTrace } from "../api/types";
import { DecisionJourney } from "../components/DecisionJourney";

const frontierPoint: ParetoPlotPoint = {
  id: "entry-stable",
  query: "Explain a stable concept",
  token_saving_proxy: 12,
  volatility: 0.1,
  objective: [-12, 0.1],
  hits: 2,
  is_candidate: false,
  is_frontier: true,
  dominated_by: [],
  is_in_cache_after: true,
};

const dominatedPoint: ParetoPlotPoint = {
  id: "entry-dominated",
  query: "A lower-saving volatile entry",
  token_saving_proxy: 4,
  volatility: 0.9,
  objective: [-4, 0.9],
  hits: 0,
  is_candidate: false,
  is_frontier: false,
  dominated_by: ["trace_candidate"],
  is_in_cache_after: true,
};

const candidatePoint: ParetoPlotPoint = {
  id: "trace_candidate",
  query: "What is the current weather today?",
  token_saving_proxy: 30,
  volatility: 0.65,
  objective: [-30, 0.65],
  hits: 0,
  is_candidate: true,
  is_frontier: true,
  dominated_by: [],
  is_in_cache_after: true,
};

const scalmTrace: SystemDecisionTrace = {
  lookup: {
    hit: false,
    similarity: 0.4,
    threshold: 0.6,
    nearest_query: "Explain a stable concept",
    nearest_entry_id: "entry-stable",
  },
  admission: {
    status: "rejected",
    rank: "low",
    reason: "SCALM rank rule rejected this candidate.",
  },
  evicted: [],
  eviction_reason: null,
  cache_before_size: 2,
  cache_was_full: false,
  cache_size: 2,
  cache: [],
};

const paretoTrace: SystemDecisionTrace = {
  lookup: {
    hit: false,
    similarity: 0.4,
    threshold: 0.5675,
    nearest_query: "Explain a stable concept",
    nearest_entry_id: "entry-stable",
  },
  admission: {
    status: "admitted",
    is_frontier: true,
    dominated_by: [],
    reason: "Candidate is non-dominated and admitted.",
  },
  evicted: [],
  eviction_reason: null,
  cache_before_size: 2,
  cache_was_full: false,
  cache_size: 3,
  cache: [],
  domain: "general",
  volatility_label: "TEMPORAL",
  volatility: 0.65,
  plot_points: [frontierPoint, dominatedPoint, candidatePoint],
};

const traceData: DecisionTraceResponse = {
  request: {
    dataset: "synthetic",
    n_queries: 3,
    capacity: 3,
    similarity_threshold: 0.6,
    warmup_count: 2,
    embedding: "mock",
    seed: 42,
    trace_index: 0,
  },
  dataset_size: 3,
  workload_index: 2,
  replay_index: 0,
  query_source: "selected dataset event",
  query: candidatePoint.query,
  candidate_answer_tokens: 20,
  answer_source: "selected dataset response; no LLM call is made",
  systems: {
    scalm: scalmTrace,
    pareto: paretoTrace,
  },
};

describe("DecisionJourney", () => {
  it("labels the classifier output and dataset source honestly", () => {
    render(<DecisionJourney data={traceData} />);

    expect(screen.getByText(/selected dataset response; no LLM call is made/)).toBeInTheDocument();
    expect(screen.getByText(/not a confidence score or ground-truth freshness measurement/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The Pareto decision" })).toBeInTheDocument();
  });

  it("provides an accessible selector and reports a selected point's dominator", () => {
    render(<DecisionJourney data={traceData} />);

    fireEvent.click(screen.getByRole("button", { name: /4 tokens · risk 0.90/ }));
    expect(screen.getByText(/Dominated by What is the current weather today/)).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });
});
