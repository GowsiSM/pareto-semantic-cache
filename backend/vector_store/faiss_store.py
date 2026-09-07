"""
FAISS-based vector store for production use.
"""
from __future__ import annotations

from typing import Optional

import faiss
import numpy as np

from backend.domain.entities import CacheEntry


class FAISSVectorStore:
    """
    FAISS-based vector store with efficient similarity search.

    Recommended for production use with >1000 entries.

    ID management: the store wraps an ``IndexFlatIP`` in an
    ``IndexIDMap`` so each entry keeps a stable external ID (its
    ``entry_id``, hashed to an int64).  ``remove()`` uses FAISS's native
    ``remove_ids``, so the index never needs a full rebuild and search
    results always map back to the correct entry.  (The previous
    implementation rebuilt the index on every removal, which renumbered
    FAISS's internal positions 0..n-1 while ``_entries`` kept the old
    keys — after any eviction, ``search()`` silently returned the wrong
    entries.)
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # IndexIDMap keeps stable external IDs; search() returns those
        # IDs directly, so results always map to the right CacheEntry.
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(dimension))
        self._entries: dict[int, CacheEntry] = {}
        self._id_counter = 0

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """L2-normalize a vector."""
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _next_id(self) -> int:
        """Return the next stable external ID for the FAISS index."""
        faiss_id = self._id_counter
        self._id_counter += 1
        return faiss_id

    def add(self, entry: CacheEntry) -> None:
        vec = np.array(entry.embedding, dtype=np.float32).reshape(1, -1)
        vec = self._normalize(vec)
        faiss_id = self._next_id()
        self.index.add_with_ids(vec, np.array([faiss_id], dtype=np.int64))
        self._entries[faiss_id] = entry
        entry._faiss_id = faiss_id  # Store ID for retrieval

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[tuple[CacheEntry, float]]:
        if self.index.ntotal == 0:
            return []

        vec = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        vec = self._normalize(vec)
        distances, indices = self.index.search(vec, min(top_k, self.index.ntotal))

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx != -1 and idx in self._entries:
                results.append((self._entries[idx], float(dist)))
        return results

    def remove(self, entry_id: str) -> None:
        # Remove by finding the entry
        for idx, entry in self._entries.items():
            if entry.entry_id == entry_id:
                del self._entries[idx]
                # FAISS supports native removal via remove_ids; no rebuild
                # needed, so external IDs stay stable.
                self.index.remove_ids(np.array([idx], dtype=np.int64))
                return

    def get(self, entry_id: str) -> Optional[CacheEntry]:
        for entry in self._entries.values():
            if entry.entry_id == entry_id:
                return entry
        return None

    def all_entries(self) -> list[CacheEntry]:
        return list(self._entries.values())

    def size(self) -> int:
        return len(self._entries)