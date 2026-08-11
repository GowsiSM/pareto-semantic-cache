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
        if not entries:
            raise ValueError("Cannot select a victim from an empty entry list")
        return min(
            entries,
            key=lambda e: (e.eviction_priority, e.created_at),
        )
