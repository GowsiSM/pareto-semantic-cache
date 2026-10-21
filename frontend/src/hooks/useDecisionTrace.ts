import { useCallback, useRef, useState } from "react";
import { ApiError, runDecisionTrace } from "../api/client";
import type { DecisionTraceResponse, TraceExperimentRequest } from "../api/types";

export type TraceStatus = "idle" | "loading" | "success" | "error";

export interface UseDecisionTraceState {
  status: TraceStatus;
  data: DecisionTraceResponse | null;
  error: string | null;
  errorDetail: string | null;
  run: (request: TraceExperimentRequest) => Promise<void>;
  reset: () => void;
}

export function useDecisionTrace(): UseDecisionTraceState {
  const [status, setStatus] = useState<TraceStatus>("idle");
  const [data, setData] = useState<DecisionTraceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (request: TraceExperimentRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("loading");
    setData(null);
    setError(null);
    setErrorDetail(null);

    try {
      const result = await runDecisionTrace(request, controller.signal);
      setData(result);
      setStatus("success");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (err instanceof ApiError) {
        setError(err.message);
        setErrorDetail(err.detail ?? null);
      } else {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
    setData(null);
    setError(null);
    setErrorDetail(null);
  }, []);

  return { status, data, error, errorDetail, run, reset };
}
