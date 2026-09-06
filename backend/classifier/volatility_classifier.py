"""Volatility classifier for the Pareto extension's signal scoring.

PROJECT-PROPOSED EXTENSION — not from the SCALM paper. The SCALM paper
(Li et al., 2024) has no volatility concept, no STABLE/TEMPORAL/PERSONAL
categories, and no "Section IV-B / V-B" content matching this. That
citation was incorrect in an earlier version of this file.

This is a simple keyword-based heuristic classifier for this project's
own volatility signal (motivation: an answer to a time-sensitive or
personal query is more likely to go stale or be wrong for a different
user than an answer to a stable factual query, so caching it long-term
is riskier). The category boundaries and volatility_score values below
are design choices, not derived from any paper or validated against
real staleness data yet — see backend/README.md for what's actually
been validated versus proposed.
"""

from __future__ import annotations

import re
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
        """Return one of {STABLE, TEMPORAL, PERSONAL}.

        BUG FIX: an earlier version used naive substring matching
        (`token in normalized`), which false-positived badly -- e.g. the
        single-character PERSONAL token "i" matches as a substring of
        "describe" and "gravity" (both contain the letter "i"), and "us"
        matches inside "discuss". Caught via
        backend/tests/pareto/test_cache.py finding a STABLE query
        classified as PERSONAL with volatility 0.85 instead of 0.0. Now
        uses word-level set membership instead of substring search.
        """
        normalized = (text or "").lower()
        if not normalized:
            return "STABLE"

        words = set(re.findall(r"[a-z0-9]+", normalized))
        if words & self.TEMPORAL_TOKENS:
            return "TEMPORAL"
        if words & self.PERSONAL_TOKENS:
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
