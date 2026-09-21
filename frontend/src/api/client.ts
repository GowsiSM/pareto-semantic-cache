import type { ExperimentRequest, ExperimentResponse, ApiErrorShape } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Calls POST {API_BASE_URL}/api/experiments/run.
 *
 * This performs a REAL request against the backend — it never fabricates
 * or substitutes local/fake results. If the backend is unreachable or
 * returns an error, this throws ApiError, and the UI must display that
 * error rather than silently showing placeholder data.
 */
export async function runExperiment(
  request: ExperimentRequest,
  signal?: AbortSignal
): Promise<ExperimentResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/experiments/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (networkError) {
    throw new ApiError(
      "Could not reach the backend API. Is it running and is VITE_API_BASE_URL correct?",
      0,
      networkError instanceof Error ? networkError.message : String(networkError)
    );
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = (await response.json()) as ApiErrorShape;
      detail = body.detail ?? body.error;
    } catch {
      // response body wasn't JSON; fall through with no detail
    }
    throw new ApiError(`Backend returned ${response.status}`, response.status, detail);
  }

  return (await response.json()) as ExperimentResponse;
}

/** Calls GET {API_BASE_URL}/api/health. Used for a simple connectivity check. */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export { API_BASE_URL };
