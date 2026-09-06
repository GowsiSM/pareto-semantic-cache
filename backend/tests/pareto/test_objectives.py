from backend.domain.entities import CacheEntry
from backend.pareto.objectives import (
    compute_token_saving_proxy,
    entry_token_saving_proxy,
    objective_vector,
)


def make_entry(query_tokens: int, answer_tokens: int) -> CacheEntry:
    return CacheEntry(
        entry_id="e1",
        query_text="q",
        answer_text="a",
        embedding=[0.1],
        pattern_id=None,
        query_token_count=query_tokens,
        answer_token_count=answer_tokens,
    )


class TestComputeTokenSavingProxy:
    def test_empty_list_returns_zero(self):
        assert compute_token_saving_proxy([]) == 0.0

    def test_single_answer_returns_its_word_count(self):
        assert compute_token_saving_proxy(["one two three"]) == 3.0

    def test_averages_across_multiple_answers(self):
        assert compute_token_saving_proxy(["one two", "one two three four"]) == 3.0


class TestEntryTokenSavingProxy:
    def test_uses_total_token_count(self):
        entry = make_entry(query_tokens=5, answer_tokens=20)
        assert entry_token_saving_proxy(entry) == 25.0


class TestObjectiveVector:
    def test_negates_token_savings_for_minimizing_convention(self):
        entry = make_entry(query_tokens=5, answer_tokens=20)
        obj = objective_vector(entry, volatility=0.3)
        assert obj[0] == -25.0

    def test_volatility_passed_through_unchanged_within_range(self):
        entry = make_entry(query_tokens=5, answer_tokens=20)
        obj = objective_vector(entry, volatility=0.3)
        assert obj[1] == 0.3

    def test_volatility_clamped_below_zero(self):
        entry = make_entry(query_tokens=5, answer_tokens=20)
        obj = objective_vector(entry, volatility=-1.0)
        assert obj[1] == 0.0

    def test_volatility_clamped_above_one(self):
        entry = make_entry(query_tokens=5, answer_tokens=20)
        obj = objective_vector(entry, volatility=5.0)
        assert obj[1] == 1.0

    def test_bigger_answer_has_more_negative_first_objective(self):
        small = objective_vector(make_entry(2, 10), volatility=0.0)
        big = objective_vector(make_entry(2, 100), volatility=0.0)
        assert big[0] < small[0]  # more negative = "better" under minimizing convention
