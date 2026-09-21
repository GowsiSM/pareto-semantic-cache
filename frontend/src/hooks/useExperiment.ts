import { useCallback, useRef, useState } from "react";
import { runExperiment, ApiError } from "../api/client";
import type { ExperimentRequest, ExperimentResponse } from "../api/types";

export type ExperimentStatus = "idle" | "loading" | "success" | "error";

export interface UseExperimentState {
  status: ExperimentStatus;
  data: ExperimentResponse | null;
  error: string | null;
  errorDetail: string | null;
  run: (request: ExperimentRequest) => Promise<void>;
  reset: () => void;
}

export function useExperiment(): UseExperimentState {
  const [status, setStatus] = useState<ExperimentStatus>("idle");
  const [data, setData] = useState<ExperimentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (request: ExperimentRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("loading");
    setError(null);
    setErrorDetail(null);

    try {
      const result = await runExperiment(request, controller.signal);
      setData(result);
      setStatus("success");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return; // superseded by a newer request; don't report as an error
      }
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
