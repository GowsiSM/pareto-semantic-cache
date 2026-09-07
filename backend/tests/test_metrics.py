"""Tests for the shared evaluation metrics (backend/evaluation/metrics.py).

Covers compute_metrics: cache hit ratio (paper Eq. 3), token saving ratio
(paper Eq. 4), staleness rate, false hit rate, admission overhead, and the
zero-division edge cases.
"""

import pytest

from backend.evaluation.metrics import EvaluationMetrics, compute_metrics


# ----------------------------------------------------------------------
# Cache hit ratio (paper Eq. 3)
# ----------------------------------------------------------------------

def test_cache_hit_ratio_basic():
    m = compute_metrics(total_queries=100, hits=25, misses=75)

    assert m.cache_hit_ratio == 0.25
    assert m.hits == 25
    assert m.misses == 75
    assert m.total_queries == 100


def test_cache_hit_ratio_all_hits():
    m = compute_metrics(total_queries=10, hits=10, misses=0)

    assert m.cache_hit_ratio == 1.0


def test_cache_hit_ratio_no_queries():
    m = compute_metrics(total_queries=0, hits=0, misses=0)

    assert m.cache_hit_ratio == 0.0


def test_total_queries_defaults_to_hits_plus_misses():
    # When total_queries is inconsistent with hits+misses, the larger wins.
    m = compute_metrics(total_queries=0, hits=3, misses=7)

    assert m.total_queries == 10
    assert m.cache_hit_ratio == 0.3


# ----------------------------------------------------------------------
# Token saving ratio (paper Eq. 4)
# ----------------------------------------------------------------------

def test_token_saving_ratio_basic():
    m = compute_metrics(
        total_queries=10, hits=5, misses=5, tokens_saved=300, total_tokens=1000
    )

    assert m.token_saving_ratio == 0.3


def test_token_saving_ratio_zero_tokens():
    m = compute_metrics(total_queries=10, hits=5, misses=5)

    assert m.token_saving_ratio == 0.0


def test_token_saving_ratio_all_saved():
    m = compute_metrics(
        total_queries=10, hits=10, misses=0, tokens_saved=500, total_tokens=500
    )

    assert m.token_saving_ratio == 1.0


# ----------------------------------------------------------------------
# Staleness rate
# ----------------------------------------------------------------------

def test_staleness_rate_basic():
    m = compute_metrics(total_queries=100, hits=40, misses=60, stale_hits=10)

    assert m.staleness_rate == 0.25  # 10 / 40


def test_staleness_rate_no_hits():
    m = compute_metrics(total_queries=100, hits=0, misses=100, stale_hits=0)

    assert m.staleness_rate == 0.0


def test_staleness_rate_all_hits_stale():
    m = compute_metrics(total_queries=10, hits=10, misses=0, stale_hits=10)

    assert m.staleness_rate == 1.0


# ----------------------------------------------------------------------
# False hit rate
# ----------------------------------------------------------------------

def test_false_hit_rate_basic():
    m = compute_metrics(total_queries=100, hits=40, misses=60, false_hits=5)

    assert m.false_hit_rate == 0.05  # 5 / 100


def test_false_hit_rate_no_queries():
    m = compute_metrics(total_queries=0, hits=0, misses=0, false_hits=0)

    assert m.false_hit_rate == 0.0


# ----------------------------------------------------------------------
# Admission overhead
# ----------------------------------------------------------------------

def test_admission_overhead_passthrough():
    m = compute_metrics(
        total_queries=100, hits=40, misses=60, admission_overhead=0.012
    )

    assert m.admission_overhead == 0.012


# ----------------------------------------------------------------------
# as_dict
# ----------------------------------------------------------------------

def test_as_dict_contains_all_fields():
    m = compute_metrics(
        total_queries=100,
        hits=40,
        misses=60,
        tokens_saved=300,
        total_tokens=1000,
        stale_hits=10,
        false_hits=5,
        admission_overhead=0.012,
    )

    d = m.as_dict()

    assert d == {
        "total_queries": 100,
        "hits": 40,
        "misses": 60,
        "token_saving_ratio": 0.3,
        "cache_hit_ratio": 0.4,
        "staleness_rate": 0.25,
        "false_hit_rate": 0.05,
        "admission_overhead": 0.012,
    }


def test_default_metrics_are_zero():
    m = EvaluationMetrics()

    assert m.as_dict() == {
        "total_queries": 0,
        "hits": 0,
        "misses": 0,
        "token_saving_ratio": 0.0,
        "cache_hit_ratio": 0.0,
        "staleness_rate": 0.0,
        "false_hit_rate": 0.0,
        "admission_overhead": 0.0,
    }