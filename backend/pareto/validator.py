"""Pareto validator: runs the ParetoCache over QA pairs and reports metrics.

Mirrors backend/scalm/validator.py's SCALMValidator shape deliberately,
so the two produce directly comparable output (same metric names, same
cold-start/replay structure) for an experiment harness to diff.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.classifier.volatility_classifier import VolatilityClassifier
from backend.embedding.token_counter import SimpleTokenCounter
from backend.pareto.cache import ParetoCache
from backend.vector_store.in_memory import InMemoryVectorStore


class ParetoValidator:
    """Validate the Pareto cache extension against QA pairs."""

    def __init__(
        self,
        capacity: int = 100,
        embedding_provider: Any = None,
        similarity_threshold: float = 0.90,
    ) -> None:
        self.capacity = capacity
        self.similarity_threshold = similarity_threshold
        if embedding_provider is None:
            # Default to the mock provider so this validator is usable
            # with zero external dependencies for logic validation; pass
            # a real provider explicitly for actual dataset experiments.
            from backend.embedding.mock_embedding import MockEmbeddingProvider

            embedding_provider = MockEmbeddingProvider()
        self.embedding_provider = embedding_provider
        self.token_counter = SimpleTokenCounter()
        self.cache = ParetoCache(
            embedding_provider=self.embedding_provider,
            vector_store=InMemoryVectorStore(),
            token_counter=self.token_counter,
            capacity=capacity,
            similarity_threshold=similarity_threshold,
        )
        self.stats = {
            "hits": 0,
            "misses": 0,
            "tokens_saved": 0,
            "total_tokens": 0,
            "llm_calls": 0,
            "stale_hits": 0,
            "false_hits": 0,
        }
        self._volatility_clf = VolatilityClassifier()

    def run(self, qa_pairs: List[Tuple[str, str]], warmup_count: int = 100) -> Dict:
        """
        Run Pareto cache validation on QA pairs. Same two-phase shape as
        SCALMValidator.run(): warm up the cache unconditionally (cold
        cache admits everything for both systems), then replay the rest
        through lookup/store and record hit/token metrics.
        """
        for query, response in qa_pairs[:warmup_count]:
            self.cache.store(query, response)

        for query, response in qa_pairs[warmup_count:]:
            response_tokens = self.token_counter.count(response)
            self.stats["total_tokens"] += response_tokens

            result = self.cache.lookup(query)

            if result.hit:
                self.stats["hits"] += 1
                self.stats["tokens_saved"] += response_tokens

                # Quality: track stale and false hits.
                #
                # BUG FIX: this used to compare result.similarity against
                # self.similarity_threshold (a fixed 0.90 reference), but
                # ParetoCache.lookup() actually decides hit/miss against
                # its own ADAPTIVE per-query threshold (domain + volatility
                # aware -- see pareto/cache.py and pareto/threshold.py),
                # which it returns as result.threshold_used. Comparing
                # against the wrong (fixed) reference flagged legitimate
                # hits as "false" whenever the adaptive threshold had been
                # lowered below 0.90 for that query -- this produced a
                # non-zero false_hit_rate that was a pure measurement
                # artifact of the adaptive-threshold mechanism, not a real
                # quality difference. GPTCache/SCALM use one fixed
                # threshold throughout, so they could never trigger this
                # bug, which is why only Pareto ever showed a nonzero
                # false_hit_rate. Now compares against the threshold that
                # was ACTUALLY used to accept the hit.
                entry_query = getattr(result.entry, "query_text", None)
                if entry_query and self._volatility_clf.volatility_score(entry_query) > 0.0:
                    self.stats["stale_hits"] += 1
                effective_threshold = (
                    result.threshold_used
                    if result.threshold_used is not None
                    else self.similarity_threshold
                )
                if result.similarity is not None and result.similarity < effective_threshold:
                    self.stats["false_hits"] += 1
            else:
                self.stats["misses"] += 1
                self.stats["llm_calls"] += 1
                self.cache.store(query, response)

        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        token_saving_rate = (
            self.stats["tokens_saved"] / self.stats["total_tokens"]
            if self.stats["total_tokens"] > 0
            else 0
        )
        staleness_rate = (
            self.stats["stale_hits"] / self.stats["hits"]
            if self.stats["hits"] > 0
            else 0
        )
        false_hit_rate = (
            self.stats["false_hits"] / self.stats["hits"]
            if self.stats["hits"] > 0
            else 0
        )

        return {
            "hit_rate": hit_rate,
            "token_saving_rate": token_saving_rate,
            "staleness_rate": staleness_rate,
            "false_hit_rate": false_hit_rate,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "stale_hits": self.stats["stale_hits"],
            "false_hits": self.stats["false_hits"],
            "total_queries": total,
            "llm_calls": self.stats["llm_calls"],
            "tokens_saved": self.stats["tokens_saved"],
            "total_tokens": self.stats["total_tokens"],
        }

    def reset(self) -> None:
        """Reset validator state."""
        self.cache = ParetoCache(
            embedding_provider=self.embedding_provider,
            vector_store=InMemoryVectorStore(),
            token_counter=self.token_counter,
            capacity=self.capacity,
            similarity_threshold=self.similarity_threshold,
        )
        self.stats = {
            "hits": 0,
            "misses": 0,
            "tokens_saved": 0,
            "total_tokens": 0,
            "llm_calls": 0,
            "stale_hits": 0,
            "false_hits": 0,
        }
        self._volatility_clf = VolatilityClassifier()
