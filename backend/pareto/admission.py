"""Joint Admission Score (JAS) for Pareto-style admission.

The paper defines JAS as a separate signal from the Pareto skyline itself:
TSR × (1 − α · vol(c)). Section V-B describes it as one of the coordinated
modules that filters candidates before the frontier pruning step in V-C.
"""

from __future__ import annotations


class JointAdmissionScore:
    """Compute the Section V-B JAS value for a candidate cache entry."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha

    def score(self, tsr: float, volatility: float) -> float:
        """Return JAS = TSR * (1 - alpha * volatility)."""
        bounded_volatility = max(0.0, min(1.0, volatility))
        return max(0.0, tsr * (1.0 - self.alpha * bounded_volatility))

    def score_candidate(self, token_saving_ratio: float, volatility: float) -> float:
        return self.score(token_saving_ratio, volatility)
