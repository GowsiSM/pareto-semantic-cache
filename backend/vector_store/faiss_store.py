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
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product = cosine (with normalized vectors)
        self._entries: dict[int, CacheEntry] = {}
        self._id_counter = 0

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """L2-normalize a vector."""
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def add(self, entry: CacheEntry) -> None:
        vec = np.array(entry.embedding, dtype=np.float32).reshape(1, -1)
        vec = self._normalize(vec)
        self.index.add(vec)
        self._entries[self._id_counter] = entry
        entry._faiss_id = self._id_counter  # Store ID for retrieval
        self._id_counter += 1

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
                # FAISS doesn't support removal; rebuild index
                self._rebuild_index()
                return

    def _rebuild_index(self) -> None:
        """Rebuild FAISS index from remaining entries."""
        if not self._entries:
            self.index = faiss.IndexFlatIP(self.dimension)
            return

        vectors = []
        new_entries = {}
        for idx, entry in self._entries.items():
            vec = np.array(entry.embedding, dtype=np.float32).reshape(1, -1)
            vec = self._normalize(vec)
            vectors.append(vec.flatten())
            new_entries[idx] = entry

        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(np.array(vectors, dtype=np.float32))

    def get(self, entry_id: str) -> Optional[CacheEntry]:
        for entry in self._entries.values():
            if entry.entry_id == entry_id:
                return entry
        return None

    def all_entries(self) -> list[CacheEntry]:
        return list(self._entries.values())

    def size(self) -> int:
        return len(self._entries)