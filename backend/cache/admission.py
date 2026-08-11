from __future__ import annotations

from typing import Optional

from backend.domain.entities import CacheEntry, PatternRank, SemanticPattern


class RankBasedAdmissionPolicy:
    """
    Faithful implementation of the paper's adaptive storage strategy
    (section IV-B):

      - Cold cache: admit queries from low-rank patterns (and above).
      - Full cache: tighten admission to mid-rank and high-rank only.

    This is (A) directly from the paper, not an extension. Unranked
    candidates (pattern=None, e.g. genuinely novel first-round queries
    with no established pattern yet) are treated as low-rank by default,
    since the paper doesn't specify unseen-pattern behavior explicitly —
    this default is our engineering interpretation (C), called out here.
    """

    def should_admit(
        self,
        candidate: CacheEntry,
        pattern: Optional[SemanticPattern],
        cache_is_full: bool,
    ) -> bool:
        rank = pattern.rank if pattern is not None else PatternRank.LOW
        if not cache_is_full:
            return True  # cold/non-full cache admits everything (low+)
        return rank in (PatternRank.MID, PatternRank.HIGH)
