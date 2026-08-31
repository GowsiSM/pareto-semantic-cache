import pytest

from backend.cache.admission import RankBasedAdmissionPolicy
from backend.cache.eviction import RankSeededLFUEviction
from backend.domain.entities import CacheEntry, PatternRank, SemanticPattern


def make_entry(entry_id: str, priority: int, created_at: float) -> CacheEntry:
    return CacheEntry(
        entry_id=entry_id,
        query_text="q",
        answer_text="a",
        embedding=[0.1, 0.2],
        pattern_id=None,
        query_token_count=1,
        answer_token_count=1,
        eviction_priority=priority,
        created_at=created_at,
    )


def make_pattern(rank: PatternRank) -> SemanticPattern:
    return SemanticPattern(
        pattern_id="p1", round_index=1, centroid=[0.1, 0.2], rank=rank
    )


class TestRankBasedAdmission:
    def test_cold_cache_admits_low_rank(self):
        policy = RankBasedAdmissionPolicy()
        candidate = make_entry("e1", priority=1, created_at=0)
        pattern = make_pattern(PatternRank.LOW)

        assert policy.should_admit(candidate, pattern, cache_is_full=False) is True

    def test_full_cache_rejects_low_rank(self):
        policy = RankBasedAdmissionPolicy()
        candidate = make_entry("e1", priority=1, created_at=0)
        pattern = make_pattern(PatternRank.LOW)

        assert policy.should_admit(candidate, pattern, cache_is_full=True) is False

    def test_full_cache_admits_mid_and_high_rank(self):
        policy = RankBasedAdmissionPolicy()
        candidate = make_entry("e1", priority=1, created_at=0)

        assert policy.should_admit(candidate, make_pattern(PatternRank.MID), True) is True
        assert policy.should_admit(candidate, make_pattern(PatternRank.HIGH), True) is True

    def test_no_pattern_defaults_to_low_rank_behavior(self):
        policy = RankBasedAdmissionPolicy()
        candidate = make_entry("e1", priority=1, created_at=0)

        assert policy.should_admit(candidate, None, cache_is_full=True) is False
        assert policy.should_admit(candidate, None, cache_is_full=False) is True


class TestRankSeededLFUEviction:
    def test_evicts_lowest_priority(self):
        policy = RankSeededLFUEviction()
        entries = [
            make_entry("low", priority=1, created_at=100),
            make_entry("mid", priority=2, created_at=100),
            make_entry("high", priority=3, created_at=100),
        ]

        victim = policy.select_victim(entries)

        assert victim.entry_id == "low"

    def test_ties_broken_by_oldest(self):
        policy = RankSeededLFUEviction()
        entries = [
            make_entry("newer", priority=1, created_at=200),
            make_entry("older", priority=1, created_at=100),
        ]

        victim = policy.select_victim(entries)

        assert victim.entry_id == "older"

    def test_hits_increase_priority_and_protect_from_eviction(self):
        policy = RankSeededLFUEviction()
        entry_a = make_entry("a", priority=1, created_at=100)
        entry_b = make_entry("b", priority=1, created_at=100)
        entry_a.record_hit()
        entry_a.record_hit()

        victim = policy.select_victim([entry_a, entry_b])

        assert victim.entry_id == "b"

    def test_empty_list_raises(self):
        policy = RankSeededLFUEviction()
        with pytest.raises(ValueError):
            policy.select_victim([])
