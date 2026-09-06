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
