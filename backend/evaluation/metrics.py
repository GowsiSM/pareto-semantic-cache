"""Evaluation metrics used to compare No Cache, GPTCache, SCALM, and this project."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    total_queries: int = 0
    hits: int = 0
    misses: int = 0
    token_saving_ratio: float = 0.0
    cache_hit_ratio: float = 0.0
    staleness_rate: float = 0.0
    false_hit_rate: float = 0.0
    admission_overhead: float = 0.0

    def as_dict(self) -> dict:
        return {
            "total_queries": self.total_queries,
            "hits": self.hits,
            "misses": self.misses,
            "token_saving_ratio": self.token_saving_ratio,
            "cache_hit_ratio": self.cache_hit_ratio,
            "staleness_rate": self.staleness_rate,
            "false_hit_rate": self.false_hit_rate,
            "admission_overhead": self.admission_overhead,
        }


def compute_metrics(
    *,
    total_queries: int,
    hits: int,
    misses: int,
    tokens_saved: int = 0,
    total_tokens: int = 0,
    stale_hits: int = 0,
    false_hits: int = 0,
    admission_overhead: float = 0.0,
) -> EvaluationMetrics:
    """Compute the shared metrics used to compare the evaluated systems."""
    total = max(total_queries, hits + misses)
    cache_hit_ratio = hits / total if total else 0.0
    token_saving_ratio = tokens_saved / total_tokens if total_tokens else 0.0
    staleness_rate = stale_hits / max(hits, 1) if hits else 0.0
    false_hit_rate = false_hits / max(total, 1) if total else 0.0

    return EvaluationMetrics(
        total_queries=total,
        hits=hits,
        misses=misses,
        token_saving_ratio=token_saving_ratio,
        cache_hit_ratio=cache_hit_ratio,
        staleness_rate=staleness_rate,
        false_hit_rate=false_hit_rate,
        admission_overhead=admission_overhead,
    )
