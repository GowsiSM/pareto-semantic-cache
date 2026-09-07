"""Joint Admission Score (JAS) for Pareto-style admission.

PROJECT-PROPOSED EXTENSION — not from the SCALM paper. The SCALM paper
(Li et al., 2024) has no "Joint Admission Score," no "Section V-B," and
no formula combining token-saving ratio with a volatility term. That
citation was incorrect in an earlier version of this file and has been
removed.

JAS = TSR × (1 − α · vol(c)) is this project's own design: a single
scalar combining token-saving ratio with a volatility penalty, used
alongside (not as a replacement for) the Pareto frontier logic in
frontier.py. Note the inherent tension: this is a weighted-score
formula, which is exactly the kind of single-objective collapsing the
Pareto approach is meant to avoid. It's kept here as one candidate
signal (e.g. for cold-start ranking, before there are enough cached
entries to compute a meaningful frontier) — not as the primary
admission mechanism once the frontier is populated.
"""

from __future__ import annotations


class JointAdmissionScore:
    """Compute this project's JAS value for a candidate cache entry."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha

    def score(self, tsr: float, volatility: float) -> float:
        """Return JAS = TSR * (1 - alpha * volatility)."""
        bounded_volatility = max(0.0, min(1.0, volatility))
        return max(0.0, tsr * (1.0 - self.alpha * bounded_volatility))

    def score_candidate(self, token_saving_ratio: float, volatility: float) -> float:
        return self.score(token_saving_ratio, volatility)
