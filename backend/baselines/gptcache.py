"""GPTCache baseline used for fair comparison against SCALM and the Pareto extension.

CORRECTION: an earlier version of this file did exact-string-match dict
lookup (`if query not in self._entries`), which is NOT a semantic cache
at all and did not match its own docstring's claim of "global similarity
threshold retrieval." It has been rewritten to actually do
embedding-based cosine similarity lookup against a flat threshold, with
no clustering and no rank-aware admission — matching what the paper's
own baseline actually is (section V-E: LFU and LRU baselines in
GPTCache, no semantic pattern awareness). The earlier "Section VI-A"
citation was also fabricated and has been removed.

Implemented by composing the existing ScalmCache orchestrator with
AlwaysAdmitPolicy + PlainLFUEviction (or PlainLRUEviction), rather than
a separate hand-rolled cache implementation — this guarantees identical
lookup/embedding/vector-store behavior to SCALM and the Pareto cache,
so the only real difference between the three systems in an experiment
is the admission/eviction policy, which is the actual thing being
compared.
"""
from __future__ import annotations

from typing import Optional

from backend.cache.admission import AlwaysAdmitPolicy
from backend.cache.eviction import PlainLFUEviction, PlainLRUEviction
from backend.cache.scalm_cache import LookupResult, ScalmCache
from backend.domain.entities import CacheEntry
from backend.interfaces.protocols import EmbeddingProvider, TokenCounter, VectorStore

DEFAULT_SIMILARITY_THRESHOLD = 0.90  # paper Table I finding; GPTCache uses a flat threshold


class GPTCache:
    """
    Flat-threshold semantic cache baseline: no clustering, no pattern
    ranks, admits everything, evicts by plain LFU (default) or LRU.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        token_counter: TokenCounter,
        capacity: int,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        eviction: str = "lfu",
    ) -> None:
        if eviction not in ("lfu", "lru"):
            raise ValueError("eviction must be 'lfu' or 'lru'")
        eviction_policy = PlainLFUEviction() if eviction == "lfu" else PlainLRUEviction()
        self._cache = ScalmCache(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            token_counter=token_counter,
            admission_policy=AlwaysAdmitPolicy(),
            eviction_policy=eviction_policy,
            capacity=capacity,
            similarity_threshold=similarity_threshold,
        )

    def lookup(self, query_text: str) -> LookupResult:
        return self._cache.lookup(query_text)

    def store(self, query_text: str, answer_text: str) -> Optional[CacheEntry]:
        # No pattern -- GPTCache has no clustering, so pattern is always None.
        return self._cache.store(query_text, answer_text, pattern=None)

    @property
    def size(self) -> int:
        return self._cache.size

    @property
    def stats(self) -> dict:
        return self._cache.stats

    def __len__(self) -> int:
        return self.size

