"""Domain classifier for the paper's Section V-D domain-aware thresholds."""

from __future__ import annotations

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
        normalized = (text or "").lower()
        if not normalized:
            return "general"

        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            scores[domain] = sum(1 for keyword in keywords if keyword in normalized)

        best_domain, best_score = max(scores.items(), key=lambda item: item[1])
        return best_domain if best_score > 0 else "general"

    def predict_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.predict(text) for text in texts]

    def domain_to_weight(self, domain: str) -> float:
        return {"medical": 1.15, "code": 1.10, "legal": 1.20, "general": 1.0}.get(domain, 1.0)

    def score_batch(self, texts: Sequence[str]) -> list[float]:
        return [self.domain_to_weight(self.predict(text)) for text in texts]
