# backend/scalm/validator.py
"""
SCALM validator: replay-driven hit-rate / token-saving measurement.

Rank assignment (the fix for the earlier freeze bug):
    After warmup, each cache miss triggers a clustering pass that groups
    the new query's embedding with all existing cache entries using
    DBSCANRoundClustering.  A token-saving-ratio (TSR) proxy is computed
    per pattern (average total_token_count of its member entries), and
    patterns are ranked by percentile: top 25 % → HIGH, next 50 % → MID,
    bottom 25 % → LOW.  The new query's pattern is stored with this rank,
    so RankBasedAdmissionPolicy correctly admits HIGH/MID entries even
    when the cache is full.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.cache.admission import RankBasedAdmissionPolicy
from backend.cache.eviction import RankSeededLFUEviction
from backend.cache.scalm_cache import ScalmCache
from backend.classifier.volatility_classifier import VolatilityClassifier
from backend.domain.entities import PatternRank, SemanticPattern
from backend.embedding.token_counter import SimpleTokenCounter
from backend.scalm.clustering import DBSCANRoundClustering
from backend.vector_store.in_memory import InMemoryVectorStore


class SCALMValidator:
    """
    Validate SCALM implementation against MOSS dataset.
    Reproduces the paper's experimental setup.

    Flow:
        1. Warmup phase  — cold cache admits every entry (LOW rank is
           fine because cache_is_full is False).
        2. Replay phase  — for each cache miss, cluster the new query
           with all existing entries, compute a TSR proxy per pattern,
           assign rank (HIGH/MID/LOW) by percentile, and store with the
           resulting rank.  RankBasedAdmissionPolicy then decides
           admission: HIGH and MID are admitted even when the cache is
           full; LOW is rejected (correctly — low-value patterns should
           not displace existing entries).
    """

    def __init__(
        self,
        capacity: int = 100,
        similarity_threshold: float = 0.90,
        embedding_provider: Optional[Any] = None,
    ):
        self.capacity = capacity
        self.threshold = similarity_threshold
        if embedding_provider is None:
            from backend.embedding.sentence_transformer_provider import (
                SentenceTransformerEmbeddingProvider,
            )
            embedding_provider = SentenceTransformerEmbeddingProvider()
        self.embedding_provider = embedding_provider
        self.token_counter = SimpleTokenCounter()
        # Keep a reference so we can read all entries for clustering.
        self._vector_store = InMemoryVectorStore()
        self._clustering = DBSCANRoundClustering(eps=0.6, min_samples=2)
        self.cache = ScalmCache(
            embedding_provider=self.embedding_provider,
            vector_store=self._vector_store,
            token_counter=self.token_counter,
            admission_policy=RankBasedAdmissionPolicy(),
            eviction_policy=RankSeededLFUEviction(),
            capacity=capacity,
            similarity_threshold=similarity_threshold,
        )
        self.stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "tokens_saved": 0,
            "total_tokens": 0,
            "llm_calls": 0,
            "stale_hits": 0,
            "false_hits": 0,
        }
        self._volatility_clf = VolatilityClassifier()

    # ------------------------------------------------------------------
    # Internal: clustering + TSR-based rank assignment
    # ------------------------------------------------------------------

    def _compute_pattern_for_query(
        self, query_embedding: list[float]
    ) -> SemanticPattern:
        """
        Cluster *query_embedding* together with every existing cache entry
        using DBSCAN, compute a TSR proxy per pattern, rank all patterns
        by percentile, and return the SemanticPattern that contains the
        new query — with rank, token_saving_ratio, centroid, and
        member_entry_ids fully populated.

        TSR proxy (per pattern): average ``total_token_count`` across its
        member CacheEntry objects.  This is a store-time approximation of
        the paper's Eq. 4 TSR; see ``backend/pareto/objectives.py``
        docstring for rationale.

        Rank thresholds: top 25 % → HIGH, next 50 % → MID, bottom 25 %
        → LOW.  When there is only one pattern it receives HIGH (the
        minimum).
        """
        all_entries = self._vector_store.all_entries()

        # Cold / empty cache — nothing to cluster against.
        if not all_entries:
            return SemanticPattern(
                pattern_id=str(uuid.uuid4()),
                round_index=1,
                centroid=query_embedding,
                rank=PatternRank.LOW,
            )

        # Build the combined embedding set for DBSCAN.
        embeddings = [e.embedding for e in all_entries]
        entry_ids = [e.entry_id for e in all_entries]

        pending_id = f"pending_{uuid.uuid4()}"
        embeddings.append(query_embedding)
        entry_ids.append(pending_id)

        patterns = self._clustering.cluster_round(
            round_index=1,
            embeddings=embeddings,
            entry_ids=entry_ids,
        )

        # TSR proxy per pattern.
        entry_by_id = {e.entry_id: e for e in all_entries}
        for pat in patterns:
            member_tokens = [
                entry_by_id[mid].total_token_count
                for mid in pat.member_entry_ids
                if mid in entry_by_id
            ]
            pat.token_saving_ratio = (
                sum(member_tokens) / len(member_tokens) if member_tokens else 0.0
            )

        # Locate the pattern that contains the pending query.
        target: Optional[SemanticPattern] = None
        for pat in patterns:
            if pending_id in pat.member_entry_ids:
                target = pat
                break

        if target is None:
            # Should never happen, but defensive fallback.
            return SemanticPattern(
                pattern_id=str(uuid.uuid4()),
                round_index=1,
                centroid=query_embedding,
                rank=PatternRank.LOW,
            )

        # Rank all patterns by TSR (descending) — percentile buckets.
        _assign_ranks_by_percentile(patterns)

        return target

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, qa_pairs: List[Tuple[str, str]], warmup_count: int = 100) -> Dict:
        """
        Run SCALM validation on QA pairs.

        Args:
            qa_pairs: List of (query, response) tuples
            warmup_count: Number of entries to warm up cache with

        Returns:
            Dict with metrics
        """
        # Step 1: Warm up cache (cold start — cache is not full, so
        # RankBasedAdmissionPolicy admits everything).
        for i, (query, response) in enumerate(qa_pairs[:warmup_count]):
            pattern = SemanticPattern(
                pattern_id=f"warm_{i}",
                round_index=1,
                centroid=[0.0] * 384,
                rank=PatternRank.LOW,
            )
            self.cache.store(query, response, pattern)

        # Step 2: Process remaining queries.
        for query, response in qa_pairs[warmup_count:]:
            response_tokens = self.token_counter.count(response)
            self.stats["total_tokens"] += response_tokens

            result = self.cache.lookup(query)

            if result.hit:
                self.stats["hits"] += 1
                self.stats["tokens_saved"] += response_tokens
                # Quality audit on the hit: a hit is "stale" if the
                # matched entry's query is volatile (TEMPORAL/PERSONAL —
                # its answer is likely to go stale or be user-specific),
                # and "false" if the hit's similarity is below the
                # configured threshold (shouldn't happen, but defensive).
                if self._volatility_clf.volatility_score(
                    result.entry.query_text
                ) > 0.0:
                    self.stats["stale_hits"] += 1
                if result.similarity is not None and result.similarity < self.threshold:
                    self.stats["false_hits"] += 1
            else:
                self.stats["misses"] += 1
                self.stats["llm_calls"] += 1
                # Cluster + rank the new query properly.
                query_embedding = self.embedding_provider.embed(query)
                pattern = self._compute_pattern_for_query(query_embedding)
                # Assign a deterministic ID; keep the computed rank/metadata.
                pattern.pattern_id = f"miss_{self.stats['llm_calls']}"
                self.cache.store(query, response, pattern)

        # Step 3: Compute metrics.
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        token_saving_rate = (
            self.stats["tokens_saved"] / self.stats["total_tokens"]
            if self.stats["total_tokens"] > 0
            else 0
        )
        staleness_rate = (
            self.stats["stale_hits"] / self.stats["hits"] if self.stats["hits"] > 0 else 0
        )
        false_hit_rate = (
            # BUG FIX: was false_hits / total (all queries). A "false hit
            # rate" should be a fraction of HITS (what fraction of the
            # hits we returned were bad), matching pareto/validator.py's
            # definition -- dividing by total silently deflated this
            # metric here relative to Pareto's, making any cross-system
            # comparison of false_hit_rate invalid even before the
            # separate adaptive-threshold bug (see pareto/validator.py).
            self.stats["false_hits"] / self.stats["hits"] if self.stats["hits"] > 0 else 0
        )

        return {
            "hit_rate": hit_rate,
            "token_saving_rate": token_saving_rate,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total_queries": total,
            "llm_calls": self.stats["llm_calls"],
            "tokens_saved": self.stats["tokens_saved"],
            "total_tokens": self.stats["total_tokens"],
            "stale_hits": self.stats["stale_hits"],
            "false_hits": self.stats["false_hits"],
            "staleness_rate": staleness_rate,
            "false_hit_rate": false_hit_rate,
        }

    def reset(self):
        """Reset cache and stats."""
        self._vector_store = InMemoryVectorStore()
        self.cache = ScalmCache(
            embedding_provider=self.embedding_provider,
            vector_store=self._vector_store,
            token_counter=self.token_counter,
            admission_policy=RankBasedAdmissionPolicy(),
            eviction_policy=RankSeededLFUEviction(),
            capacity=self.capacity,
            similarity_threshold=self.threshold,
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


def _assign_ranks_by_percentile(patterns: list[SemanticPattern]) -> None:
    """
    Assign HIGH/MID/LOW ranks by TSR percentile, matching the paper's
    buckets: top 25 % → HIGH, next 50 % → MID, bottom 25 % → LOW.

    (mid_cutoff is the top-75 % boundary, NOT 50 % — a 50 % boundary
    would give HIGH=25 %, MID=25 %, LOW=50 %, making SCALM twice as
    strict as the paper intends.)
    """
    sorted_patterns = sorted(
        patterns, key=lambda p: p.token_saving_ratio, reverse=True
    )
    n = len(sorted_patterns)
    high_cutoff = max(1, math.ceil(n * 0.25))
    mid_cutoff = max(high_cutoff + 1, math.ceil(n * 0.75))

    for i, pat in enumerate(sorted_patterns):
        if i < high_cutoff:
            pat.rank = PatternRank.HIGH
        elif i < mid_cutoff:
            pat.rank = PatternRank.MID
        else:
            pat.rank = PatternRank.LOW