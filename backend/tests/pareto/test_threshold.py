import pytest

from backend.pareto.threshold import AdaptiveThresholdAdapter


class TestAdaptiveThresholdAdapter:
    def test_general_domain_zero_volatility_returns_base(self):
        adapter = AdaptiveThresholdAdapter(base_threshold=0.90, beta=0.05)
        assert adapter.compute(domain="general", volatility=0.0) == pytest.approx(0.90)

    def test_medical_domain_raises_threshold(self):
        adapter = AdaptiveThresholdAdapter(base_threshold=0.90, beta=0.05)
        result = adapter.compute(domain="medical", volatility=0.0)
        assert result > 0.90  # medical should require a stricter (higher) match

    def test_higher_volatility_lowers_threshold(self):
        adapter = AdaptiveThresholdAdapter(base_threshold=0.90, beta=0.05)
        low_vol = adapter.compute(domain="general", volatility=0.0)
        high_vol = adapter.compute(domain="general", volatility=1.0)
        assert high_vol < low_vol

    def test_result_clamped_to_valid_range(self):
        adapter = AdaptiveThresholdAdapter(base_threshold=0.99, beta=0.5)
        result = adapter.compute(domain="legal", volatility=0.0)
        assert 0.0 <= result <= 1.0

    def test_unknown_domain_falls_back_to_no_adjustment(self):
        adapter = AdaptiveThresholdAdapter(base_threshold=0.90, beta=0.05)
        result = adapter.compute(domain="not_a_real_domain", volatility=0.0)
        assert result == pytest.approx(0.90)

    def test_adapt_for_query_matches_compute(self):
        adapter = AdaptiveThresholdAdapter()
        assert adapter.adapt_for_query(domain="code", volatility=0.2) == adapter.compute(
            domain="code", volatility=0.2
        )