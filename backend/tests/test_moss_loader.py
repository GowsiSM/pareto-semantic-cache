"""Tests for the MOSS dataset loader.

MOSS format (verified against moss-sample-10k.jsonl):
{
    "conversation_id": 1,
    "meta_instruction": "...",
    "num_turns": 5,
    "chat": {
        "turn_1": {"Human": "<|Human|>: ...<eoh>\\n", "MOSS": "<|MOSS|>: ...<eom>\\n", ...},
        "turn_2": {...}
    },
    "category": "Brainstorming"
}
"""

import json

import pytest

from backend.experiment.moss_loader import MOSSLoader


def _write_jsonl(tmp_path, rows):
    path = tmp_path / "moss_sample.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


def _moss_row(chat, category="Brainstorming", conversation_id=1, num_turns=None):
    return {
        "conversation_id": conversation_id,
        "meta_instruction": "You are MOSS.",
        "num_turns": num_turns if num_turns is not None else len(chat),
        "chat": chat,
        "category": category,
    }


def _turn(human, moss):
    return {
        "Human": f"<|Human|>: {human}<eoh>\n",
        "Inner Thoughts": "<|Inner Thoughts|>: None<eot>\n",
        "Commands": "<|Commands|>: None<eoc>\n",
        "Tool Responses": "<|Results|>: None<eor>\n",
        "MOSS": f"<|MOSS|>: {moss}<eom>\n",
    }


# ----------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------

def test_loads_conversations(tmp_path):
    rows = [
        _moss_row({"turn_1": _turn("q1", "a1")}, conversation_id=1),
        _moss_row({"turn_1": _turn("q2", "a2")}, conversation_id=2),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))

    assert len(loader) == 2
    assert loader.conversations[0]["conversation_id"] == 1
    assert loader.conversations[1]["conversation_id"] == 2


def test_limit_respects_valid_rows(tmp_path):
    rows = [
        _moss_row({"turn_1": _turn("q1", "a1")}),
        _moss_row({"turn_1": _turn("q2", "a2")}),
        _moss_row({"turn_1": _turn("q3", "a3")}),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path), limit=2)

    assert len(loader) == 2


def test_skips_malformed_json_lines(tmp_path):
    path = tmp_path / "moss_sample.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write('{"conversation_id": 1, "chat": {}}\n')
        handle.write("this is not json\n")
        handle.write('{"conversation_id": 2, "chat": {}}\n')

    loader = MOSSLoader(str(path))

    assert len(loader) == 2


def test_missing_file_returns_empty(tmp_path):
    loader = MOSSLoader(str(tmp_path / "does_not_exist.jsonl"))

    assert len(loader) == 0
    assert loader.get_stats()["total_conversations"] == 0


def test_skips_blank_lines(tmp_path):
    path = tmp_path / "moss_sample.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write('{"conversation_id": 1, "chat": {}}\n')
        handle.write("\n")
        handle.write('{"conversation_id": 2, "chat": {}}\n')

    loader = MOSSLoader(str(path))

    assert len(loader) == 2


# ----------------------------------------------------------------------
# Text cleaning
# ----------------------------------------------------------------------

def test_clean_text_removes_special_tokens():
    loader = MOSSLoader("nonexistent.jsonl")  # empty loader, just for _clean_text

    cleaned = loader._clean_text(
        "<|Human|>: What is ML?<eoh>\n<|MOSS|>: Machine learning.<eom>\n"
    )

    assert cleaned == "What is ML?\nMachine learning."


def test_clean_text_removes_arbitrary_special_tokens():
    loader = MOSSLoader("nonexistent.jsonl")

    cleaned = loader._clean_text("Hello <|weird|> world")

    assert cleaned == "Hello  world"


# ----------------------------------------------------------------------
# Pair extraction
# ----------------------------------------------------------------------

def test_get_first_turn_pairs_extracts_human_moss(tmp_path):
    rows = [
        _moss_row(
            {
                "turn_1": _turn("What is ML?", "Machine learning is..."),
                "turn_2": _turn("And DL?", "Deep learning is..."),
            }
        ),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_first_turn_pairs()

    assert len(pairs) == 1
    assert pairs[0] == ("What is ML?", "Machine learning is...")


def test_get_first_turn_pairs_skips_empty_after_cleaning(tmp_path):
    rows = [
        _moss_row({"turn_1": _turn("", "")}),
        _moss_row({"turn_1": _turn("real q", "real a")}),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_first_turn_pairs()

    assert len(pairs) == 1
    assert pairs[0] == ("real q", "real a")


def test_get_first_turn_pairs_skips_missing_keys(tmp_path):
    rows = [
        _moss_row({"turn_1": {"Human": "<|Human|>: only human<eoh>\n"}}),
        _moss_row({"turn_1": _turn("q", "a")}),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_first_turn_pairs()

    assert len(pairs) == 1
    assert pairs[0] == ("q", "a")


def test_get_all_turns_pairs_extracts_every_pair(tmp_path):
    rows = [
        _moss_row(
            {
                "turn_1": _turn("q1", "a1"),
                "turn_2": _turn("q2", "a2"),
                "turn_3": _turn("q3", "a3"),
            }
        ),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_all_turns_pairs()

    assert len(pairs) == 3
    assert pairs == [("q1", "a1"), ("q2", "a2"), ("q3", "a3")]


def test_get_all_turns_pairs_sorts_by_turn_key(tmp_path):
    # Keys out of order in the JSON — must still come back sorted.
    rows = [
        _moss_row(
            {
                "turn_3": _turn("q3", "a3"),
                "turn_1": _turn("q1", "a1"),
                "turn_2": _turn("q2", "a2"),
            }
        ),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_all_turns_pairs()

    assert pairs == [("q1", "a1"), ("q2", "a2"), ("q3", "a3")]


def test_get_turns_by_category_filters(tmp_path):
    rows = [
        _moss_row({"turn_1": _turn("q1", "a1")}, category="Brainstorming"),
        _moss_row({"turn_1": _turn("q2", "a2")}, category="Coding"),
        _moss_row({"turn_1": _turn("q3", "a3")}, category="Brainstorming"),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_turns_by_category("Brainstorming")

    assert len(pairs) == 2
    assert pairs == [("q1", "a1"), ("q3", "a3")]


def test_get_turns_by_category_unknown_returns_empty(tmp_path):
    rows = [_moss_row({"turn_1": _turn("q1", "a1")}, category="Coding")]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    pairs = loader.get_turns_by_category("Brainstorming")

    assert pairs == []


# ----------------------------------------------------------------------
# Stats
# ----------------------------------------------------------------------

def test_get_stats_counts_conversations_turns_categories(tmp_path):
    rows = [
        _moss_row(
            {"turn_1": _turn("q1", "a1"), "turn_2": _turn("q2", "a2")},
            category="Brainstorming",
        ),
        _moss_row({"turn_1": _turn("q3", "a3")}, category="Coding"),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))
    stats = loader.get_stats()

    assert stats["total_conversations"] == 2
    assert stats["total_turns"] == 3
    assert stats["avg_turns_per_conversation"] == 1.5
    assert stats["categories"] == {"Brainstorming": 1, "Coding": 1}


def test_get_stats_empty_loader():
    loader = MOSSLoader("nonexistent.jsonl")
    stats = loader.get_stats()

    assert stats["total_conversations"] == 0
    assert stats["total_turns"] == 0
    assert stats["avg_turns_per_conversation"] == 0
    assert stats["categories"] == {}


def test_len_matches_loaded_count(tmp_path):
    rows = [_moss_row({"turn_1": _turn("q", "a")}) for _ in range(5)]
    path = _write_jsonl(tmp_path, rows)

    loader = MOSSLoader(str(path))

    assert len(loader) == 5