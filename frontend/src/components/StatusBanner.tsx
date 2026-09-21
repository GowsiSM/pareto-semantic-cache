import type { ExperimentStatus } from "../hooks/useExperiment";
import { API_BASE_URL } from "../api/client";

interface StatusBannerProps {
  status: ExperimentStatus;
  error: string | null;
  errorDetail: string | null;
}

export function StatusBanner({ status, error, errorDetail }: StatusBannerProps) {
  if (status === "idle") {
    return (
      <div className="status-banner status-idle">
        No experiment has been run yet. Configure the options above and press
        "Run experiment" to call the backend at{" "}
        <code>{API_BASE_URL}</code>.
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="status-banner status-loading">
        Running experiment against the backend — this calls the real
        validators, nothing here is simulated.
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="status-banner status-error">
        <div>{error}</div>
        {errorDetail && <div className="status-detail">{errorDetail}</div>}
      </div>
    );
  }

  return null;
}
