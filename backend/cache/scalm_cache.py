from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from backend.domain.entities import CacheEntry, PatternRank, SemanticPattern
from backend.interfaces.protocols import (
    AdmissionPolicy,
    EmbeddingProvider,
    EvictionPolicy,
    TokenCounter,
    VectorStore,
)

DEFAULT_SIMILARITY_THRESHOLD = 0.90  # paper Table I finding


@dataclass
class LookupResult:
    hit: bool
    entry: Optional[CacheEntry]
    similarity: Optional[float]


class ScalmCache:
    """
    Milestone 0 orchestrator. Deliberately minimal:

      - lookup(): embed query, search vector store, return hit/miss above
        the similarity threshold.
      - store(): embed + count tokens, build a CacheEntry, run it through
        the admission policy, evict via the eviction policy if the cache
        is full and the entry is admitted, then add to the vector store.

    NOT included yet (intentionally, per the roadmap):
      - pattern rank computation / re-ranking (needs a full clustering
        pass across a batch, not a single insert) — Milestone 1.
      - request coalescing / stampede protection — Phase 10.
      - cache-safety / multi-tenant identity — a later, explicitly scoped
        extension (see note in domain/entities.py).
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        token_counter: TokenCounter,
        admission_policy: AdmissionPolicy,
        eviction_policy: EvictionPolicy,
        capacity: int,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self._embedding = embedding_provider
        self._store = vector_store
        self._tokens = token_counter
        self._admission = admission_policy
        self._eviction = eviction_policy
        self._capacity = capacity
        self._threshold = similarity_threshold

    def lookup(self, query_text: str) -> LookupResult:
        query_embedding = self._embedding.embed(query_text)
        candidates = self._store.search(query_embedding, top_k=1)
        if not candidates:
            return LookupResult(hit=False, entry=None, similarity=None)

        entry, similarity = candidates[0]
        if similarity >= self._threshold:
            entry.record_hit()
            return LookupResult(hit=True, entry=entry, similarity=similarity)
        return LookupResult(hit=False, entry=None, similarity=similarity)

    def store(
        self,
        query_text: str,
        answer_text: str,
        pattern: Optional[SemanticPattern] = None,
    ) -> Optional[CacheEntry]:
        embedding = self._embedding.embed(query_text)
        candidate = CacheEntry(
            entry_id=str(uuid.uuid4()),
            query_text=query_text,
            answer_text=answer_text,
            embedding=embedding,
            pattern_id=pattern.pattern_id if pattern else None,
            query_token_count=self._tokens.count(query_text),
            answer_token_count=self._tokens.count(answer_text),
            eviction_priority=_priority_for_rank(pattern.rank if pattern else PatternRank.LOW),
        )

        cache_is_full = self._store.size() >= self._capacity
        if not self._admission.should_admit(candidate, pattern, cache_is_full):
            return None

        if cache_is_full:
            victim = self._eviction.select_victim(self._store.all_entries())
            self._store.remove(victim.entry_id)

        self._store.add(candidate)
        return candidate

    @property
    def size(self) -> int:
        return self._store.size()


def _priority_for_rank(rank: PatternRank) -> int:
    return {PatternRank.HIGH: 3, PatternRank.MID: 2, PatternRank.LOW: 1}[rank]
