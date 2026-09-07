"""Adaptive threshold adapter for Pareto semantic-cache admission.

PROJECT-PROPOSED EXTENSION — not from the SCALM paper. The SCALM paper
(Li et al., 2024) sets a single fixed similarity threshold (0.90, from
its Table I analysis) and does not vary it by domain or volatility.
"Section V-D" and "domain-aware threshold adaptation" as paper concepts
were incorrect in an earlier version of this file.

This is this project's own extension: lower the effective threshold
(more permissive matching) for lower-volatility (safer) domains, and
raise the effective bar (via the volatility penalty term) for queries
classified as more volatile. The specific formula and domain adjustment
values below are design choices made for this project, not measured or
derived from any paper.
"""

from __future__ import annotations


class AdaptiveThresholdAdapter:
    """Compute a domain-adjusted similarity threshold."""

    DOMAIN_TAU_ADJUSTMENTS = {
        "medical": 0.04,
        "code": 0.03,
        "legal": 0.05,
        "general": 0.0,
    }

    def __init__(self, base_threshold: float = 0.90, beta: float = 0.05) -> None:
        self.base_threshold = base_threshold
        self.beta = beta

    def compute(self, *, domain: str = "general", volatility: float = 0.0) -> float:
        domain_adjustment = self.DOMAIN_TAU_ADJUSTMENTS.get(domain.lower(), 0.0)
        volatility_penalty = self.beta * volatility
        return min(1.0, max(0.0, self.base_threshold + domain_adjustment - volatility_penalty))

    def adapt_for_query(self, *, domain: str, volatility: float) -> float:
        return self.compute(domain=domain, volatility=volatility)
