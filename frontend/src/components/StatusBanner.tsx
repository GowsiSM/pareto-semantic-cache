import { useEffect, useState } from "react";
import type { ExperimentStatus } from "../hooks/useExperiment";
import { API_BASE_URL } from "../api/client";

interface StatusBannerProps {
  status: ExperimentStatus;
  error: string | null;
  errorDetail: string | null;
}

function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

/**
 * Shows real, honestly-measured elapsed time while a request is in
 * flight. Deliberately does NOT show fake per-step progress ("embedding
 * queries...", "running SCALM...") since the backend runs everything in
 * a single request/response and we have no real signal for those
 * sub-steps -- inventing them would be exactly the kind of fabricated
 * status this project has been careful to avoid elsewhere.
 */
function useElapsedSeconds(active: boolean): number {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsed(0);
      return;
    }
    const start = performance.now();
    const interval = window.setInterval(() => {
      setElapsed((performance.now() - start) / 1000);
    }, 100);
    return () => window.clearInterval(interval);
  }, [active]);

  return elapsed;
}

export function StatusBanner({ status, error, errorDetail }: StatusBannerProps) {
  const elapsed = useElapsedSeconds(status === "loading");

  if (status === "idle") {
    return (
      <div className="status-banner status-idle">
        No experiment has been run yet. Configure the options above and press
        "Run experiment" to call the backend at <code>{API_BASE_URL}</code>.
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="status-banner status-loading" role="status" aria-live="polite">
        <Spinner />
        <div>
          <div className="status-loading-title">Running experiment against the backend…</div>
          <div className="status-detail">
            {elapsed.toFixed(1)}s elapsed — this calls the real validators; nothing
            here is simulated. A real-data (MOSS) run downloads the embedding
            model on first use and can take noticeably longer than the
            synthetic run.
          </div>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="status-banner status-error" role="alert">
        <div>{error}</div>
        {errorDetail && <div className="status-detail">{errorDetail}</div>}
      </div>
    );
  }

  return null;
}
