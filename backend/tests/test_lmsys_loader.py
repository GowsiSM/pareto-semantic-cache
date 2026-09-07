"""Regression tests for the LMSYS-Chat-1M loader schema fix.

The original loader guessed a MOSS-style schema (``chat``/``messages``
with ``Human``/``MOSS`` keys). The real LMSYS-Chat-1M schema uses an
OpenAI chat format: a top-level ``conversation`` list of messages with
``role`` and ``content`` keys. These tests lock in the correct schema.
"""

import json

import pytest

from backend.experiment.lmsys_loader import LMSYSLoader


def _write_jsonl(tmp_path, rows):
    path = tmp_path / "lmsys_sample.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


def _real_lmsys_row(conversation, **overrides):
    """Build a row matching the real LMSYS-Chat-1M schema."""
    row = {
        "conversation_id": "abc123",
        "model": "gpt-4",
        "conversation": conversation,
        "turn": len(conversation),
        "language": "English",
        "openai_moderation": [{"categories": {}} for _ in conversation],
        "redacted": False,
    }
    row.update(overrides)
    return row


# ----------------------------------------------------------------------
# Schema loading
# ----------------------------------------------------------------------

def test_loads_real_lmsys_schema(tmp_path):
    rows = [
        _real_lmsys_row([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]),
        _real_lmsys_row([
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
        ]),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path)

    assert len(loader) == 2


def test_rejects_moss_style_schema(tmp_path):
    """The old guessed schema (chat/messages + Human/MOSS) must be rejected."""
    rows = [
        {
            "conversation_id": 1,
            "chat": {
                "turn_1": {"Human": "Hello", "MOSS": "Hi"},
            },
        },
        {
            "conversation_id": 2,
            "messages": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
        },
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path)

    # Neither row has a valid top-level 'conversation' list
    assert len(loader) == 0
    assert loader._schema_errors


def test_skips_malformed_json_lines(tmp_path):
    path = tmp_path / "lmsys_sample.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write('{"conversation": [{"role": "user", "content": "ok"}, {"role": "assistant", "content": "yes"}]}\n')
        handle.write("this is not json\n")
        handle.write('{"conversation": [{"role": "user", "content": "ok"}, {"role": "assistant", "content": "yes"}]}\n')

    loader = LMSYSLoader(path)

    assert len(loader) == 2


def test_skips_rows_with_missing_message_keys(tmp_path):
    rows = [
        _real_lmsys_row([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]),
        # Missing 'content' on the second message
        _real_lmsys_row([
            {"role": "user", "content": "Hello"},
            {"role": "assistant"},
        ]),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path)

    assert len(loader) == 1
    assert loader._schema_errors


def test_limit_respects_valid_rows(tmp_path):
    rows = [
        _real_lmsys_row([
            {"role": "user", "content": f"q{i}"},
            {"role": "assistant", "content": f"a{i}"},
        ])
        for i in range(5)
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path, limit=3)

    assert len(loader) == 3


# ----------------------------------------------------------------------
# Query interface
# ----------------------------------------------------------------------

def test_get_first_turn_pairs_uses_role_content(tmp_path):
    rows = [
        _real_lmsys_row([
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path)
    pairs = loader.get_first_turn_pairs()

    assert pairs == [("First question", "First answer")]


def test_get_all_turn_pairs_extracts_every_pair(tmp_path):
    rows = [
        _real_lmsys_row([
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
        ]),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path)
    pairs = loader.get_all_turn_pairs()

    assert pairs == [("q1", "a1"), ("q2", "a2")]


def test_get_stats_reports_models_and_languages(tmp_path):
    rows = [
        _real_lmsys_row(
            [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}],
            model="gpt-4",
            language="English",
        ),
        _real_lmsys_row(
            [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}],
            model="claude-2",
            language="English",
        ),
    ]
    path = _write_jsonl(tmp_path, rows)

    loader = LMSYSLoader(path)
    stats = loader.get_stats()

    assert stats["total_conversations"] == 2
    assert stats["total_turns"] == 4
    assert stats["models"] == {"gpt-4": 1, "claude-2": 1}
    assert stats["languages"] == {"English": 2}
    assert stats["schema_errors"] == 0


def test_missing_file_returns_empty(tmp_path):
    loader = LMSYSLoader(tmp_path / "does-not-exist.jsonl")
    assert len(loader) == 0
