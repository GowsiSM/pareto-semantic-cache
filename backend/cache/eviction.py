"""
SCALM-style rank-seeded LFU eviction policy.
"""
from __future__ import annotations

from backend.domain.entities import CacheEntry


class RankSeededLFUEviction:
    """
    Faithful implementation of the paper's eviction strategy (section IV-C):

      - New entries start with eviction_priority set by pattern rank at
        admission time (3=high, 2=mid, 1=other) — set by the caller when
        the CacheEntry is created, not here.
      - Each cache hit increments eviction_priority (CacheEntry.record_hit).
      - On eviction, remove the entry with the LOWEST eviction_priority.
      - Ties broken by oldest `created_at` (paper: "an older query is
        evicted").
    """

    def select_victim(self, entries: list[CacheEntry]) -> CacheEntry:
        """
        Select victim with lowest priority; tie broken by oldest.
        Uses manual loop for better performance than min() with lambda.
        """
        if not entries:
            raise ValueError("Cannot select a victim from an empty entry list")

        victim = entries[0]
        for entry in entries[1:]:
            if (entry.eviction_priority < victim.eviction_priority or
                (entry.eviction_priority == victim.eviction_priority and
                 entry.created_at < victim.created_at)):
                victim = entry
        return victim