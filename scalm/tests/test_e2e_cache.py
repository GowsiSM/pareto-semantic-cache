from scalm.cache.admission import RankBasedAdmissionPolicy
from scalm.cache.eviction import RankSeededLFUEviction
from scalm.cache.scalm_cache import ScalmCache
from scalm.domain.entities import PatternRank, SemanticPattern
from scalm.embedding.mock_embedding import MockEmbeddingProvider
from scalm.embedding.token_counter import SimpleTokenCounter
from scalm.vector_store.in_memory import InMemoryVectorStore


def build_cache(capacity: int = 100, threshold: float = 0.80) -> ScalmCache:
    # threshold lowered from the paper's 0.90 default because
    # MockEmbeddingProvider is bag-of-words, not a real semantic model;
    # exact word overlap gives high similarity but not 0.90+ for paraphrases.
    # A real embedding model in a later milestone should use 0.90.
    return ScalmCache(
        embedding_provider=MockEmbeddingProvider(dimensions=128),
        vector_store=InMemoryVectorStore(),
        token_counter=SimpleTokenCounter(),
        admission_policy=RankBasedAdmissionPolicy(),
        eviction_policy=RankSeededLFUEviction(),
        capacity=capacity,
        similarity_threshold=threshold,
    )


def test_miss_then_store_then_hit_on_identical_query():
    cache = build_cache()

    miss = cache.lookup("How do I reset my password?")
    assert miss.hit is False

    cache.store("How do I reset my password?", "Go to settings and click reset.")

    hit = cache.lookup("How do I reset my password?")
    assert hit.hit is True
    assert hit.entry.answer_text == "Go to settings and click reset."
    assert hit.entry.hit_count == 1


def test_dissimilar_query_is_a_miss():
    cache = build_cache()
    cache.store("How do I reset my password?", "Go to settings and click reset.")

    result = cache.lookup("What's the capital of France?")

    assert result.hit is False


def test_full_cache_evicts_lowest_priority_entry():
    cache = build_cache(capacity=2, threshold=0.80)
    cache.store("query one about topic alpha", "answer one")
    cache.store("query two about topic beta", "answer two")
    assert cache.size == 2

    # Hit "query one" to raise its priority above "query two"
    cache.lookup("query one about topic alpha")

    # Store a third entry with a MID-rank pattern: on a full cache, only
    # mid/high-rank candidates are admitted at all (paper section IV-B),
    # so this is the entry that will actually trigger eviction.
    mid_pattern = SemanticPattern(
        pattern_id="p-mid", round_index=1, centroid=[0.0], rank=PatternRank.MID
    )
    cache.store("query three about topic gamma", "answer three", pattern=mid_pattern)

    assert cache.size == 2
    # "query two" (never hit, same starting priority) should have been evicted
    remaining_queries = {e.query_text for e in cache._store.all_entries()}
    assert "query two about topic beta" not in remaining_queries
    assert "query one about topic alpha" in remaining_queries


def test_store_returns_none_when_admission_rejects():
    cache = build_cache(capacity=1, threshold=0.80)
    cache.store("first query", "first answer")
    assert cache.size == 1

    # Cache is now full; a low-rank (pattern=None) candidate should still be
    # ADMITTED here because admission only tightens once cache_is_full is
    # True at the time of the *next* store call — verifying that path:
    result = cache.store("second query", "second answer")
    # Admission policy treats pattern=None as LOW rank, and full-cache
    # behavior rejects LOW rank -> should be rejected (None returned).
    assert result is None
    assert cache.size == 1
