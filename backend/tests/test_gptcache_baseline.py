from backend.baselines.gptcache import GPTCache
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.embedding.token_counter import SimpleTokenCounter
from backend.vector_store.in_memory import InMemoryVectorStore


def build_gptcache(capacity: int = 10, eviction: str = "lfu") -> GPTCache:
    return GPTCache(
        embedding_provider=MockEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
        token_counter=SimpleTokenCounter(),
        capacity=capacity,
        eviction=eviction,
    )


class TestGPTCacheIsActuallySemantic:
    def test_semantically_similar_but_not_identical_query_can_hit(self):
        """
        Regression test for the original bug: the old GPTCache did exact
        string-match dict lookup, so it could NEVER hit on a rephrased
        but semantically similar query -- contradicting its own claim of
        doing similarity-threshold retrieval. This test would have
        failed against the old implementation for the identical-text
        case even, since lookup(query) took a raw query with no
        similarity computation at all wired to embeddings.
        """
        cache = build_gptcache()
        cache.store("how do I reset my password", "go to settings and click reset")

        result = cache.lookup("how do I reset my password")  # identical text, should hit
        assert result.hit is True

    def test_dissimilar_query_is_a_miss(self):
        cache = build_gptcache()
        cache.store("how do I reset my password", "go to settings and click reset")

        result = cache.lookup("what is the capital of France")
        assert result.hit is False

    def test_no_pattern_or_clustering_involved(self):
        """GPTCache must never receive/require a SemanticPattern -- store()
        signature intentionally has no pattern parameter."""
        cache = build_gptcache()
        entry = cache.store("some query", "some answer")
        assert entry is not None
        assert entry.pattern_id is None


class TestGPTCacheAdmissionIsFlat:
    def test_admits_everything_regardless_of_frequency_until_full(self):
        cache = build_gptcache(capacity=2)
        assert cache.store("query one", "answer one") is not None
        assert cache.store("query two", "answer two") is not None
        assert cache.size == 2

    def test_lfu_eviction_removes_least_hit_entry(self):
        cache = build_gptcache(capacity=2, eviction="lfu")
        cache.store("query one about topic alpha", "answer one")
        cache.store("query two about topic beta", "answer two")
        cache.lookup("query one about topic alpha")  # bump its hit count

        cache.store("query three about topic gamma", "answer three")

        remaining = {e.query_text for e in cache._cache._store.all_entries()}
        assert "query two about topic beta" not in remaining

    def test_invalid_eviction_name_raises(self):
        import pytest

        with pytest.raises(ValueError):
            build_gptcache(eviction="not_a_real_policy")


class TestGPTCacheStats:
    def test_len_matches_size(self):
        cache = build_gptcache()
        cache.store("query one", "answer one")
        assert len(cache) == cache.size == 1
