# test_loader.py
"""
Real-data smoke tests for the MOSS loader.

These tests exercise MOSSLoader against the actual moss-sample-10k.jsonl
file when it is present locally. The file is gitignored (it is a large
downloaded dataset), so the tests SKIP when it is absent — CI and fresh
clones will skip, local runs with the data will validate.

Synthetic-data unit tests for MOSSLoader live in test_moss_loader.py.
"""

from pathlib import Path

import pytest

from backend.experiment.moss_loader import MOSSLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SAMPLE_CANDIDATES = [
    PROJECT_ROOT / "data" / "moss-sample-10k.jsonl",
    PROJECT_ROOT / "moss-sample-10k.jsonl",
]

SAMPLE_PATH = next((p for p in SAMPLE_CANDIDATES if p.exists()), SAMPLE_CANDIDATES[0])

pytestmark = pytest.mark.skipif(
    not SAMPLE_PATH.exists(),
    reason="moss-sample-10k.jsonl not present (gitignored dataset)",
)


def test_loads_real_sample():
    loader = MOSSLoader(str(SAMPLE_PATH))

    assert len(loader) > 0


def test_real_sample_extracts_first_turn_pairs():
    loader = MOSSLoader(str(SAMPLE_PATH))
    pairs = loader.get_first_turn_pairs()

    assert len(pairs) > 0
    for question, answer in pairs[:5]:
        assert question.strip()
        assert answer.strip()
        # Cleaned text must not retain MOSS special tokens.
        assert "<|Human|>" not in question
        assert "<|MOSS|>" not in answer
        assert "<eoh>" not in question
        assert "<eom>" not in answer


def test_real_sample_stats_are_consistent():
    loader = MOSSLoader(str(SAMPLE_PATH))
    stats = loader.get_stats()

    assert stats["total_conversations"] == len(loader)
    assert stats["total_turns"] >= stats["total_conversations"]
    assert stats["avg_turns_per_conversation"] > 0
    assert isinstance(stats["categories"], dict)
    assert len(stats["categories"]) > 0