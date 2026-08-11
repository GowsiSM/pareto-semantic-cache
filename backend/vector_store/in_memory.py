from __future__ import annotations

import math
from typing import Optional

from scalm.domain.entities import CacheEntry


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Embedding dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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

    def add(self, entry: CacheEntry) -> None:
        self._entries[entry.entry_id] = entry

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[CacheEntry, float]]:
        scored = [
            (entry, cosine_similarity(query_embedding, entry.embedding))
            for entry in self._entries.values()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def remove(self, entry_id: str) -> None:
        self._entries.pop(entry_id, None)

    def get(self, entry_id: str) -> Optional[CacheEntry]:
        return self._entries.get(entry_id)

    def all_entries(self) -> list[CacheEntry]:
        return list(self._entries.values())

    def size(self) -> int:
        return len(self._entries)
