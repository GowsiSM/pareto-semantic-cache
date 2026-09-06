"""Domain classifier for the Pareto extension's domain-aware thresholds.

PROJECT-PROPOSED EXTENSION — not from the SCALM paper. There is no
"Section V-D" or domain-bucket concept in the SCALM paper (Li et al.,
2024). That citation was incorrect in an earlier version of this file.

Simple keyword-based domain classifier used only to feed
threshold.AdaptiveThresholdAdapter. The domain list and keyword sets
below are design choices for this project, not derived from any paper.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence


class DomainClassifier:
    """Classify a request into one of the paper's domain buckets."""

    DOMAIN_KEYWORDS = {
        "medical": {"doctor", "patient", "diagnosis", "symptom", "treatment", "medication", "clinic"},
        "code": {"python", "javascript", "function", "debug", "compiler", "api", "class", "import", "error"},
        "legal": {"contract", "law", "liability", "court", "regulation", "compliance", "attorney", "lease"},
        "general": {"how", "what", "why", "when", "compare", "summarize", "explain"},
    }

    def predict(self, text: str) -> str:
        """
        BUG FIX: an earlier version used naive substring matching
        (`keyword in normalized`), same class of bug found and fixed in
        volatility_classifier.py (e.g. "how" would match inside
        unrelated words containing that substring). Now uses word-level
        set membership.
        """
        normalized = (text or "").lower()
        if not normalized:
            return "general"

        words = set(re.findall(r"[a-z0-9]+", normalized))
        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            scores[domain] = len(words & keywords)

        best_domain, best_score = max(scores.items(), key=lambda item: item[1])
        return best_domain if best_score > 0 else "general"

    def predict_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.predict(text) for text in texts]

    def domain_to_weight(self, domain: str) -> float:
        return {"medical": 1.15, "code": 1.10, "legal": 1.20, "general": 1.0}.get(domain, 1.0)

    def score_batch(self, texts: Sequence[str]) -> list[float]:
        return [self.domain_to_weight(self.predict(text)) for text in texts]
