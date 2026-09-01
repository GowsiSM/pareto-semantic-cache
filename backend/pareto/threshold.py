"""Adaptive threshold adapter for Pareto semanti-cache admission.

This implements the paper's domain-aware threshold adaptation described in
Section V-D: τ = τ_base + β * something, with domain-specific adjustments such
as medical/legal/code variations.
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
