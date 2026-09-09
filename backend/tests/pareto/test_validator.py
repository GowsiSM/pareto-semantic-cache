from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.pareto.validator import ParetoValidator


class TestParetoValidator:
    def test_run_returns_expected_metric_keys(self):
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        qa_pairs = [
            ("what is the capital of France", "Paris"),
            ("what is the capital of France", "Paris"),
            ("describe gravity", "a force " * 10),
        ]

        result = validator.run(qa_pairs, warmup_count=1)

        expected_keys = {
            "hit_rate", "token_saving_rate", "hits", "misses",
            "total_queries", "llm_calls", "tokens_saved", "total_tokens",
        }
        assert expected_keys.issubset(result.keys())

    def test_exact_repeat_query_produces_a_hit(self):
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        qa_pairs = [
            ("how do I reset my password", "go to settings"),
            ("how do I reset my password", "go to settings"),
        ]

        result = validator.run(qa_pairs, warmup_count=1)

        assert result["hits"] == 1
        assert result["misses"] == 0

    def test_no_repeats_produces_zero_hits(self):
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        qa_pairs = [
            ("completely unique query alpha", "answer alpha"),
            ("completely unique query beta", "answer beta"),
            ("completely unique query gamma", "answer gamma"),
        ]

        result = validator.run(qa_pairs, warmup_count=1)

        assert result["hits"] == 0

    def test_reset_clears_stats_and_cache(self):
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        validator.run([("q", "a"), ("q", "a")], warmup_count=1)
        assert validator.cache.size > 0

        validator.reset()

        assert validator.cache.size == 0
        assert validator.stats["hits"] == 0

    def test_defaults_to_mock_embedding_provider_when_none_given(self):
        # Must not attempt to load a real (network-dependent) model when
        # no provider is explicitly passed.
        validator = ParetoValidator(capacity=5)
        assert validator.embedding_provider is not None
        result = validator.run([("q", "a"), ("q", "a")], warmup_count=1)
        assert result["hits"] == 1


class _FakeLookupResult:
    def __init__(self, hit, entry, similarity, threshold_used):
        self.hit = hit
        self.entry = entry
        self.similarity = similarity
        self.threshold_used = threshold_used


class _FakeEntry:
    def __init__(self, query_text):
        self.query_text = query_text


class _FakeCacheForcingAdaptiveThreshold:
    """
    Fake cache standing in for ParetoCache, letting us deterministically
    control similarity and threshold_used without depending on real
    embedding fuzziness -- see test_false_hit_regression below.
    """

    def __init__(self, similarity, threshold_used, query_text="describe gravity"):
        self._similarity = similarity
        self._threshold_used = threshold_used
        self._query_text = query_text
        self.size = 0

    def lookup(self, query_text):
        return _FakeLookupResult(
            hit=True,
            entry=_FakeEntry(self._query_text),
            similarity=self._similarity,
            threshold_used=self._threshold_used,
        )

    def store(self, query_text, answer_text):
        pass


class TestFalseHitRegression:
    """
    Regression tests for a real bug: the false-hit check compared
    result.similarity against a fixed self.similarity_threshold (e.g.
    0.90), but ParetoCache.lookup() actually decides hits against its
    own ADAPTIVE per-query threshold (domain + volatility aware) and
    returns it as result.threshold_used. Any hit accepted under a
    lowered adaptive threshold (similarity between the adaptive
    threshold and the fixed 0.90 reference) was incorrectly counted as
    a "false hit" even though it was a legitimate hit under Pareto's
    own real admission logic.
    """

    def test_hit_accepted_under_lowered_adaptive_threshold_is_not_a_false_hit(self):
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        # similarity=0.87 was accepted because threshold_used=0.85 (e.g. a
        # volatile query that lowered the adaptive threshold below the
        # fixed 0.90 reference). This must NOT count as a false hit.
        validator.cache = _FakeCacheForcingAdaptiveThreshold(
            similarity=0.87, threshold_used=0.85
        )

        result = validator.run([("q1", "a1"), ("q2", "a2")], warmup_count=0)

        assert result["hits"] == 2
        assert result["false_hits"] == 0

    def test_hit_genuinely_below_its_own_threshold_used_is_still_flagged(self):
        # If similarity is somehow below the threshold that was actually
        # used to accept it (shouldn't normally happen, but this is the
        # defensive check's real purpose), it should still be flagged.
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        validator.cache = _FakeCacheForcingAdaptiveThreshold(
            similarity=0.80, threshold_used=0.85
        )

        result = validator.run([("q1", "a1"), ("q2", "a2")], warmup_count=0)

        assert result["false_hits"] == 2

    def test_false_hit_rate_denominator_is_hits_not_total(self):
        validator = ParetoValidator(capacity=10, embedding_provider=MockEmbeddingProvider())
        validator.cache = _FakeCacheForcingAdaptiveThreshold(
            similarity=0.80, threshold_used=0.85
        )

        result = validator.run([("q1", "a1")] * 4, warmup_count=0)

        assert result["hits"] == 4
        assert result["false_hits"] == 4
        assert result["false_hit_rate"] == 1.0  # 4/4 hits, not 4/total-including-warmup
