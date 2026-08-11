"""
Core interfaces. The SCALM algorithm layer (cache/) depends only on these
abstractions, never on a concrete embedding provider, vector store, or
database. This lets us test the algorithm with in-memory fakes and swap
infrastructure later without touching algorithm code.

Using typing.Protocol (structural typing) rather than ABCs so test doubles
don't need to subclass anything.
"""
from __future__ import annotations

from typing import Protocol, Optional
from backend.domain.entities import CacheEntry, SemanticPattern


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for a single piece of text."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""
        ...


class VectorStore(Protocol):
    def add(self, entry: CacheEntry) -> None:
        ...

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[CacheEntry, float]]:
        """Return (entry, cosine_similarity) pairs, most similar first."""
        ...

    def remove(self, entry_id: str) -> None:
        ...

    def get(self, entry_id: str) -> Optional[CacheEntry]:
        ...

    def all_entries(self) -> list[CacheEntry]:
        ...

    def size(self) -> int:
        ...


class ClusteringPolicy(Protocol):
    def cluster_round(
        self,
        round_index: int,
        embeddings: list[list[float]],
        entry_ids: list[str],
    ) -> list[SemanticPattern]:
        """Cluster one conversation round's embeddings into patterns."""
        ...


class AdmissionPolicy(Protocol):
    def should_admit(
        self,
        candidate: CacheEntry,
        pattern: Optional[SemanticPattern],
        cache_is_full: bool,
    ) -> bool:
        ...


class EvictionPolicy(Protocol):
    def select_victim(self, entries: list[CacheEntry]) -> CacheEntry:
        """Choose which entry to evict when the cache is full."""
        ...


class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        ...
