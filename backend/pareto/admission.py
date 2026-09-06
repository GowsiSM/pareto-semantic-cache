"""Project-proposed Joint Admission Score (JAS) for Pareto-style admission.

JAS is an extension proposed by this project, not a mechanism defined by the
SCALM paper. It combines token-saving ratio (TSR) with a normalized volatility
signal before Pareto-style admission.
"""

from __future__ import annotations


class JointAdmissionScore:
    """Compute the project's proposed JAS value for a candidate cache entry."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha

    def score(self, tsr: float, volatility: float) -> float:
        """Return JAS = TSR * (1 - alpha * volatility)."""
        bounded_volatility = max(0.0, min(1.0, volatility))
        return max(0.0, tsr * (1.0 - self.alpha * bounded_volatility))

    def score_candidate(self, token_saving_ratio: float, volatility: float) -> float:
        return self.score(token_saving_ratio, volatility)
