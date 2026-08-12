"""
Mock embedding provider for testing and CI.
"""
from __future__ import annotations

import re
import hashlib

# Pre-compile regex pattern for performance
_WORD_PATTERN = re.compile(r"[a-z0-9]+")

# Minimal stopword list. The paper explicitly calls for "removing
# excessive stop words" as part of similarity preprocessing (section IV-A).
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "and", "or", "but", "with",
    "what", "how", "can", "could", "would", "should", "do", "does", "did",
    "i", "you", "he", "she", "it", "we", "they", "this", "that", "like",
    "today", "now",
}


class MockEmbeddingProvider:
    """
    Deterministic, dependency-free embedding provider for tests and CI.

    Implementation: hashed bag-of-words. Each distinct word hashes to a
    fixed dimension index; the resulting sparse vector is L2-normalized.
    This is NOT a real semantic embedding — it only captures lexical
    overlap — but that's sufficient and appropriate for unit-testing
    admission/eviction/clustering logic without a real model or network
    access. It must NOT be used to validate SCALM's reported hit-ratio
    numbers; that requires a real embedding model (e.g.
    text-embedding-3-small, as the paper uses) in a later benchmark phase.
    """

    def __init__(self, dimensions: int = 512) -> None:
        # 512 chosen empirically: at 64-128 dims, hash collisions between
        # unrelated words produced spurious cosine similarity (~0.35
        # between genuinely unrelated sentences), which broke clustering
        # tests. At 512 dims collisions become negligible for short texts.
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        words = _WORD_PATTERN.findall(text.lower())
        # Filter stopwords (set lookup is O(1))
        words = [w for w in words if w not in _STOPWORDS]
        if not words:
            return vec

        # Hash each word using MD5 (deterministic across runs)
        for word in words:
            idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % self.dimensions
            vec[idx] += 1.0

        # L2 normalize
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]