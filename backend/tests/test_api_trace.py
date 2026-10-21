from backend import api
from backend.embedding.mock_embedding import MockEmbeddingProvider


def test_trace_replays_real_cache_decisions_and_objectives(monkeypatch):
    qa_pairs = [
        ("Explain stable number theory", "A stable answer about number theory."),
        ("Describe basic data structures", "A short response about structures."),
        (
            "What is the current weather in Chennai today?",
            "Current weather changes throughout the day and should be checked live.",
        ),
    ]
    monkeypatch.setattr(api, "_load_pairs", lambda _request: qa_pairs)
    monkeypatch.setattr(api, "_build_embedding", lambda _request: MockEmbeddingProvider())

    request = api.TraceRequest(
        dataset="synthetic",
        n_queries=3,
        capacity=2,
        similarity_threshold=0.99,
        warmup_count=2,
        embedding="mock",
        seed=42,
        trace_index=0,
    )

    result = api._replay_trace(request)

    assert result["query"] == qa_pairs[2][0]
    assert result["answer_source"].startswith("selected dataset response")
    assert result["systems"]["scalm"]["lookup"]["threshold"] == 0.99
    assert result["systems"]["pareto"]["lookup"]["threshold"] is not None
    assert result["systems"]["pareto"]["volatility"] == 0.65
    assert len(result["systems"]["pareto"]["plot_points"]) == 3

    candidate = result["systems"]["pareto"]["plot_points"][-1]
    expected_tokens = len(qa_pairs[2][0].split()) + len(qa_pairs[2][1].split())
    assert candidate["token_saving_proxy"] == expected_tokens
    assert candidate["objective"] == [-float(expected_tokens), 0.65]


def test_trace_request_rejects_an_index_outside_the_replay_phase():
    try:
        api.TraceRequest(
            dataset="synthetic",
            n_queries=3,
            capacity=2,
            warmup_count=2,
            trace_index=1,
        )
    except ValueError as error:
        assert "after the warmup phase" in str(error)
    else:
        raise AssertionError("out-of-range trace index should be rejected")


def test_custom_query_trace_requires_a_candidate_response():
    try:
        api.TraceRequest(
            dataset="synthetic",
            n_queries=3,
            capacity=2,
            warmup_count=2,
            trace_index=0,
            query_text="What is the current weather?",
        )
    except ValueError as error:
        assert "provided together" in str(error)
    else:
        raise AssertionError("custom query without a response should be rejected")


def test_custom_query_is_replayed_and_response_is_not_echoed_back(monkeypatch):
    qa_pairs = [
        ("Stable cache seed one", "short answer one"),
        ("Stable cache seed two", "short answer two"),
        ("unused selected row", "unused row response"),
    ]
    monkeypatch.setattr(api, "_load_pairs", lambda _request: qa_pairs)
    monkeypatch.setattr(api, "_build_embedding", lambda _request: MockEmbeddingProvider())
    request = api.TraceRequest(
        dataset="synthetic",
        n_queries=3,
        capacity=2,
        warmup_count=2,
        trace_index=0,
        query_text="What is the current weather today?",
        answer_text="A user supplied candidate answer.",
    )

    result = api._replay_trace(request)

    assert result["query"] == request.query_text
    assert result["query_source"] == "user input"
    assert result["answer_source"].startswith("user-provided candidate response")
    assert "answer_text" not in result["request"]
    assert result["candidate_answer_tokens"] == len(request.answer_text.split())


def test_non_full_cache_can_admit_a_dominated_candidate_and_trace_both_facts(monkeypatch):
    qa_pairs = [
        (
            "Explain a very detailed stable fact about astronomy",
            "A long stable explanation about astronomy and the planets.",
        ),
        ("unused replay query", "unused answer"),
    ]
    monkeypatch.setattr(api, "_load_pairs", lambda _request: qa_pairs)
    monkeypatch.setattr(api, "_build_embedding", lambda _request: MockEmbeddingProvider())
    request = api.TraceRequest(
        dataset="synthetic",
        n_queries=2,
        capacity=10,
        similarity_threshold=1.0,
        warmup_count=1,
        trace_index=0,
        query_text="A short stable fact",
        answer_text="Short answer.",
    )

    result = api._replay_trace(request)
    pareto = result["systems"]["pareto"]
    candidate = next(point for point in pareto["plot_points"] if point["is_candidate"])

    assert not pareto["cache_was_full"]
    assert pareto["admission"]["status"] == "admitted"
    assert not pareto["admission"]["is_frontier"]
    assert candidate["is_in_cache_after"]
    assert pareto["cache_size"] == 2


def test_rejecting_a_dominated_candidate_does_not_evict_a_cached_entry(monkeypatch):
    qa_pairs = [
        (
            "Explain a very detailed stable fact about astronomy",
            "A long stable explanation about astronomy and the planets.",
        ),
        ("unused replay query", "unused answer"),
    ]
    monkeypatch.setattr(api, "_load_pairs", lambda _request: qa_pairs)
    monkeypatch.setattr(api, "_build_embedding", lambda _request: MockEmbeddingProvider())
    request = api.TraceRequest(
        dataset="synthetic",
        n_queries=2,
        capacity=1,
        similarity_threshold=1.0,
        warmup_count=1,
        trace_index=0,
        query_text="A short stable fact",
        answer_text="Short answer.",
    )

    pareto = api._replay_trace(request)["systems"]["pareto"]
    candidate = next(point for point in pareto["plot_points"] if point["is_candidate"])

    assert pareto["cache_was_full"]
    assert pareto["admission"]["status"] == "rejected"
    assert not candidate["is_in_cache_after"]
    assert pareto["evicted"] == []
    assert pareto["cache_size"] == 1
