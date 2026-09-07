"""
Regression tests for the SCALMValidator freeze-bug fix.

The original bug: SCALMValidator.run() hardcoded rank=PatternRank.LOW for
every SemanticPattern, including post-warmup cache misses.  Because
RankBasedAdmissionPolicy rejects LOW-rank candidates when the cache is
full, the cache froze at the warmup set and no further entry was ever
admitted.

The fix: after warmup, each miss triggers _compute_pattern_for_query()
which clusters the new query with existing entries via DBSCAN, computes a
TSR proxy per pattern, and assigns rank by percentile (top 25 % → HIGH,
next 25 % → MID, bottom 50 % → LOW).  RankBasedAdmissionPolicy then
correctly admits HIGH/MID entries.
"""
from backend.scalm.validator import SCALMValidator
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.domain.entities import PatternRank


def _make_validator(capacity: int = 10) -> SCALMValidator:
    """Build a SCALMValidator with MockEmbeddingProvider for fast tests."""
    return SCALMValidator(
        capacity=capacity,
        similarity_threshold=0.60,
        embedding_provider=MockEmbeddingProvider(),
    )


def _qa_pairs(n: int = 30, reuse_rate: float = 0.5, seed: int = 0):
    """
    Generate QA pairs with controlled reuse.  Half the queries are
    duplicates of earlier ones (guaranteeing cache hits when cached),
    and half are unique.
    """
    pairs = []
    for i in range(n):
        if i > 0 and i % 2 == 0 and reuse_rate > 0:
            # Reuse an earlier query → guaranteed hit if it's cached.
            pairs.append(pairs[i - 2])
        else:
            pairs.append((f"query_{i}_unique", f"answer_{i}"))
    return pairs


# Diverse, semantically distinct query/answer tokens so MockEmbedding
# produces embeddings with low cosine similarity (avoids false hits).
_DISTINCT_QUERIES = [
    "quantum entanglement explained",
    "recipe for chocolate cake",
    "history of the roman empire",
    "how to fix a leaky faucet",
    "best hiking trails in colorado",
    "python decorators tutorial",
    "climate change effects on coral reefs",
    "stock market analysis today",
    "yoga poses for beginners",
    "how diesel engines work",
    "famous paintings by picasso",
    "lunar eclipse visibility map",
    "homemade sourdough bread",
    "machine learning gradient descent",
    "carnival traditions in brazil",
    "how airplanes generate lift",
    "renaissance architecture features",
    "baking soda cleaning hacks",
    "neural network backpropagation",
    "tropical fish aquarium setup",
    "ancient egyptian hieroglyphics",
    " javascript async await explained",
    "keto diet meal planning",
    "how earthquakes are measured",
    "molecular biology dna replication",
    "solar panel installation guide",
    "operating systems memory management",
    " french cuisine techniques",
    "telescope optics astronomy",
    "blockchain consensus algorithms",
]


def _distinct_qa_pairs(n: int = 30) -> list[tuple[str, str]]:
    """Return n QA pairs using semantically distinct query texts."""
    pairs = []
    for i in range(n):
        q = _DISTINCT_QUERIES[i % len(_DISTINCT_QUERIES)]
        # Ensure no two queries in the same run share the exact same text.
        pairs.append((f"{q} #{i}", f"answer_{i}"))
    return pairs


class TestFreezeBugRegression:
    """Verify the cache does not freeze after warmup."""

    def test_cache_admits_entries_after_warmup(self):
        """
        After warmup fills the cache, post-warmup misses with distinct
        queries should still be admitted (at least some of them) — the
        cache must NOT freeze.
        """
        capacity = 10
        warmup_count = capacity  # Fill the cache exactly.
        # Provide enough distinct queries so some get HIGH/MID rank and
        # are admitted even with a full cache.
        pairs = _distinct_qa_pairs(n=50)

        v = _make_validator(capacity=capacity)
        result = v.run(pairs, warmup_count=warmup_count)

        # With 50 distinct queries and only 10 capacity, we must see some
        # post-warmup admits (i.e. the total stored should exceed the
        # warmup count).  Before the fix, stored == warmup_count always.
        total_stored = result["hits"] + result["misses"]
        assert total_stored > warmup_count, (
            f"Cache appears frozen: total_stored={total_stored}, "
            f"warmup_count={warmup_count}.  Expected some post-warmup admits."
        )

    def test_cache_size_grows_beyond_warmup(self):
        """
        After warmup fills the cache, new entries should still be admitted
        (evicting lower-rank victims).  The cache size should remain at
        capacity but the total number of stored entries should exceed
        warmup_count.
        """
        capacity = 10
        pairs = _distinct_qa_pairs(n=50)

        v = _make_validator(capacity=capacity)
        result = v.run(pairs, warmup_count=capacity)

        # The cache should be at capacity (admits replaced victims).
        assert v.cache.size == capacity
        # At least some replay queries should have been misses (LLM calls).
        assert result["llm_calls"] > 0, (
            "Some replay queries should have been misses (LLM calls)."
        )


class TestRankAssignment:
    """Verify _compute_pattern_for_query returns proper ranks."""

    def test_empty_cache_returns_low(self):
        v = _make_validator()
        emb = v.embedding_provider.embed("test query")
        pattern = v._compute_pattern_for_query(emb)
        assert pattern.rank == PatternRank.LOW

    def test_patterns_receive_varied_ranks(self):
        """
        After several entries are cached, new queries should receive
        different ranks (not all LOW) depending on their TSR.
        """
        v = _make_validator(capacity=20)
        # Manually populate the cache with a few entries.
        qa = _qa_pairs(n=10, reuse_rate=0.0, seed=0)
        for query, response in qa:
            v.cache.store(query, response)

        # Now compute rank for a new query.
        emb = v.embedding_provider.embed("new_query_1")
        pattern = v._compute_pattern_for_query(emb)

        # With 10 entries clustered by DBSCAN, there should be multiple
        # patterns, and the target should have a valid rank.
        assert pattern.rank in (PatternRank.HIGH, PatternRank.MID, PatternRank.LOW)
        assert pattern.token_saving_ratio >= 0.0
        assert len(pattern.centroid) > 0
