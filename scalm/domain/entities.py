"""
Domain entities for SCALM.

These are plain data objects with no dependency on storage, embedding
providers, or any infrastructure. This is deliberate (see interfaces.py) —
the algorithm layer must be testable with pure in-memory objects and mocks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import uuid


class PatternRank(str, Enum):
    """Rank bucket assigned to a semantic pattern (paper: top 25/50/75%)."""
    HIGH = "high"
    MID = "mid"
    LOW = "low"


@dataclass(frozen=True)
class Query:
    """A single user query within a (possibly multi-round) conversation."""
    text: str
    conversation_id: str
    round_index: int  # 1-indexed round number within the conversation
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class CacheEntry:
    """
    A stored (query, answer) pair plus the bookkeeping SCALM needs for
    admission/ranking/eviction decisions.

    NOTE on cache identity (see section 15/9 of the spec): the paper never
    addresses model/system-prompt/tenant identity. We deliberately do NOT
    bake that into Milestone 0 — this entity is a faithful reproduction of
    what the paper caches (query text + embedding + answer + pattern
    membership). Cache-safety fields (model, tenant, system_prompt_hash)
    are a planned extension for a later milestone, not part of this one.
    """
    entry_id: str
    query_text: str
    answer_text: str
    embedding: list[float]
    pattern_id: Optional[str]  # which semantic pattern this belongs to
    query_token_count: int
    answer_token_count: int
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    hit_count: int = 0
    # Eviction priority value per paper section IV-C:
    # 3 = high-rank pattern, 2 = mid-rank, 1 = other. Hits increment it.
    eviction_priority: int = 1

    def record_hit(self) -> None:
        self.hit_count += 1
        self.last_accessed_at = time.time()
        self.eviction_priority += 1

    @property
    def total_token_count(self) -> int:
        return self.query_token_count + self.answer_token_count


@dataclass
class SemanticPattern:
    """
    A cluster of semantically related queries for one conversation round,
    as produced by CO-HSC / SE-HSC (paper section IV-B).
    """
    pattern_id: str
    round_index: int
    centroid: list[float]
    member_entry_ids: list[str] = field(default_factory=list)
    token_saving_ratio: float = 0.0
    proportion_ratio: float = 0.0  # share of dataset weight this pattern holds
    rank: PatternRank = PatternRank.LOW
