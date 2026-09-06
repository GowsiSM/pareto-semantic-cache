"""Project-proposed volatility classifier for cache signal scoring.

The stable, temporal, and personal categories are an engineering extension
introduced by this project, not a classification scheme defined by SCALM.
This lightweight implementation avoids a heavyweight training pipeline.
"""

from __future__ import annotations

from typing import Iterable, Sequence


class VolatilityClassifier:
    """Assign a volatility label to a query or conversation snippet."""

    TEMPORAL_TOKENS = {
        "today",
        "tomorrow",
        "yesterday",
        "now",
        "recently",
        "week",
        "month",
        "year",
        "time",
        "date",
        "when",
        "current",
        "upcoming",
    }
    PERSONAL_TOKENS = {
        "my",
        "me",
        "i",
        "mine",
        "our",
        "us",
        "personal",
        "favorite",
        "myself",
        "home",
        "workplace",
        "job",
    }

    def predict(self, text: str) -> str:
        """Return one of {STABLE, TEMPORAL, PERSONAL}."""
        normalized = (text or "").lower()
        if not normalized:
            return "STABLE"

        if any(token in normalized for token in self.TEMPORAL_TOKENS):
            return "TEMPORAL"
        if any(token in normalized for token in self.PERSONAL_TOKENS):
            return "PERSONAL"
        return "STABLE"

    def predict_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.predict(text) for text in texts]

    def volatility_score(self, text: str) -> float:
        """Map the label to a normalized volatility score in [0, 1]."""
        label = self.predict(text)
        return {"STABLE": 0.0, "TEMPORAL": 0.65, "PERSONAL": 0.85}[label]

    def score_batch(self, texts: Sequence[str]) -> list[float]:
        return [self.volatility_score(text) for text in texts]
