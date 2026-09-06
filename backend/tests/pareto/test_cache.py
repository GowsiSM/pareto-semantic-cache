from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.embedding.token_counter import SimpleTokenCounter
from backend.pareto.cache import ParetoCache
from backend.vector_store.in_memory import InMemoryVectorStore


def build_cache(capacity: int) -> ParetoCache:
    return ParetoCache(
        embedding_provider=MockEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
        token_counter=SimpleTokenCounter(),
        capacity=capacity,
    )


class TestParetoCacheColdStart:
    def test_cold_cache_admits_everything_up_to_capacity(self):
        cache = build_cache(capacity=3)
        assert cache.store("query one", "answer one") is not None
        assert cache.store("query two", "answer two") is not None
        assert cache.store("query three", "answer three") is not None
        assert cache.size == 3

    def test_miss_then_store_then_hit_on_identical_query(self):
        cache = build_cache(capacity=10)
        miss = cache.lookup("how do I reset my password")
        assert miss.hit is False

        cache.store("how do I reset my password", "go to settings and click reset")

        hit = cache.lookup("how do I reset my password")
        assert hit.hit is True
        assert hit.entry.answer_text == "go to settings and click reset"


class TestParetoCacheFullCacheAdmission:
    def test_dominated_candidate_is_rejected(self):
        """A candidate with fewer tokens AND equal-or-worse volatility,
        relative to an existing entry, must be rejected -- it can never
        improve the Pareto-optimal set."""
        cache = build_cache(capacity=1)
        cache.store("describe gravity in detail", "word " * 50)  # big answer, STABLE

        result = cache.store("describe gravity briefly", "word " * 5)  # smaller answer, STABLE
        assert result is None
        remaining = cache._store.all_entries()
        assert len(remaining) == 1
        assert remaining[0].query_text == "describe gravity in detail"

    def test_non_dominated_candidate_replaces_a_dominated_entry(self):
        """A candidate that's NOT dominated by the existing entry (better
        on at least the volatility axis, matching or trading off on
        tokens) should be admitted, evicting the now-dominated entry."""
        cache = build_cache(capacity=1)
        cache.store("what is my schedule today", "word " * 20)  # PERSONAL+TEMPORAL, high volatility

        # Same token count, but STABLE -- dominates the existing entry
        # (equal tokens, strictly lower volatility).
        result = cache.store("describe gravity", "word " * 20)
        assert result is not None
        remaining = cache._store.all_entries()
        assert len(remaining) == 1
        assert remaining[0].query_text == "describe gravity"

    def test_regression_equal_tokens_temporal_candidate_correctly_rejected(self):
        """
        Regression test for the volatility-classifier substring bug found
        during development: 'describe gravity' was misclassified as
        PERSONAL (volatility 0.85) due to the letter 'i' matching as a
        substring, which incorrectly let a worse (TEMPORAL) candidate with
        equal token count evict a genuinely better (STABLE) entry. After
        the fix, a STABLE entry must correctly dominate and survive
        against an equal-token TEMPORAL candidate.
        """
        cache = build_cache(capacity=1)
        cache.store("describe gravity", "word " * 20)  # STABLE

        result = cache.store("describe today", "word " * 20)  # TEMPORAL, same token count

        assert result is None
        remaining = cache._store.all_entries()
        assert remaining[0].query_text == "describe gravity"

    def test_regression_reference_point_must_be_worst_case_not_best_case(self):
        """
        Regression test for the inverted reference-point bug: an earlier
        version used a very negative number as the 'worst case' for the
        token objective, when the worst case is actually 0 (since
        objective = -token_count and token_count >= 0). This test just
        needs a full cache + a new candidate to exercise the hypervolume
        code path without raising ValueError.
        """
        cache = build_cache(capacity=2)
        cache.store("first query here", "word " * 10)
        cache.store("second query here", "word " * 15)

        # Must not raise -- this call exercises _admit_to_full_cache's
        # hypervolume computation.
        result = cache.store("third query with a much bigger answer", "word " * 100)
        assert cache.size == 2  # capacity respected regardless of outcome


class TestParetoCacheStats:
    def test_hit_rate_reported_correctly(self):
        cache = build_cache(capacity=10)
        cache.store("query one", "answer one")
        cache.lookup("query one")  # hit
        cache.lookup("totally unrelated query about spacecraft")  # miss

        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 1
        assert cache.stats["hit_rate"] == 0.5
