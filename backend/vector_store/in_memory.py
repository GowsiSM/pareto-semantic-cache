"""
In-memory vector store with cosine similarity search.
"""
from __future__ import annotations

import math
from typing import Optional

from backend.domain.entities import CacheEntry


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two normalized vectors."""
    # Assumes vectors are already normalized (checked on add)
    dot = sum(x * y for x, y in zip(a, b))
    return max(0.0, min(1.0, dot))  # Clamp for numerical stability


class InMemoryVectorStore:
    """
    Brute-force cosine similarity search over an in-memory dict.

    Deliberately O(n) per search. Fine for Milestone 0 correctness testing
    and small benchmarks. Section 14 flags this explicitly as a candidate
    for replacement (pgvector/Qdrant/FAISS) once we're past algorithm
    validation and need to benchmark at realistic cache sizes.
    """

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def _normalize(self, vec: list[float]) -> list[float]:
        """L2-normalize a vector."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return vec
        return [x / norm for x in vec]

    def add(self, entry: CacheEntry) -> None:
        """Add entry with normalized embedding."""
        entry.embedding = self._normalize(entry.embedding)
        self._entries[entry.entry_id] = entry

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[CacheEntry, float]]:
        """Search for most similar entries (O(n) brute force)."""
        query = self._normalize(query_embedding)
        scored = [
            (entry, cosine_similarity(query, entry.embedding))
            for entry in self._entries.values()
        ]
        # Use sort for simplicity (n log n); for large n, consider heapq.nlargest
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def remove(self, entry_id: str) -> None:
        """Remove entry by ID."""
        self._entries.pop(entry_id, None)

    def get(self, entry_id: str) -> Optional[CacheEntry]:
        """Get entry by ID."""
        return self._entries.get(entry_id)

    def all_entries(self) -> list[CacheEntry]:
        """Return all entries."""
        return list(self._entries.values())

    def size(self) -> int:
        """Return number of entries."""
        return len(self._entries)