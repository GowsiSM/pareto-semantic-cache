"""Loader for the LMSYS-Chat-1M dataset used by the paper's audit and experiments.

LMSYS-Chat-1M schema (confirmed from HuggingFace + public codebases):
    {
        "conversation_id": str,        # unique conversation identifier
        "model": str,                  # LLM that produced the response
        "conversation": [              # OpenAI chat format
            {"role": "user",      "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ],
        "turn": int,                   # number of turns
        "language": str,               # detected language
        "openai_moderation": list,     # per-message moderation flags
        "redacted": bool,              # PII redaction flag
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


class LMSYSLoader:
    """Loader for the LMSYS-Chat-1M dataset (OpenAI chat format).

    Each conversation's ``conversation`` field is a list of messages with
    ``role`` (``"user"`` / ``"assistant"`` / ``"system"``) and ``content``
    keys — the standard OpenAI chat completions format.

    The loader validates the schema of each row on load and reports
    malformed entries rather than silently returning empty results.
    """

    # Required top-level keys (conversation_id and model are metadata-only)
    _REQUIRED_KEYS = {"conversation"}

    def __init__(self, file_path: str | Path, limit: Optional[int] = None) -> None:
        self.file_path = Path(file_path)
        self.limit = limit
        self.conversations: list[dict] = []
        self._schema_errors: list[str] = []
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.file_path.exists():
            print(f"LMSYS dataset not found: {self.file_path}")
            return

        loaded = 0
        skipped_schema = 0
        skipped_json = 0

        with self.file_path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if self.limit is not None and loaded >= self.limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    skipped_json += 1
                    continue

                # --- schema validation ---
                missing = self._REQUIRED_KEYS - row.keys()
                if missing:
                    skipped_schema += 1
                    self._schema_errors.append(
                        f"line {index}: missing keys {missing}"
                    )
                    continue

                conversation = row["conversation"]
                if not isinstance(conversation, list) or not conversation:
                    skipped_schema += 1
                    self._schema_errors.append(
                        f"line {index}: 'conversation' is empty or not a list"
                    )
                    continue

                # Validate each message has role + content
                valid = True
                for msg_i, msg in enumerate(conversation):
                    if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                        skipped_schema += 1
                        self._schema_errors.append(
                            f"line {index}, message {msg_i}: "
                            f"missing 'role' or 'content' key"
                        )
                        valid = False
                        break

                if valid:
                    self.conversations.append(row)
                    loaded += 1

        if skipped_json:
            print(f"Skipped {skipped_json} malformed JSON lines")
        if skipped_schema:
            print(f"Skipped {skipped_schema} lines with schema errors "
                  f"({len(self._schema_errors)} recorded)")
        if self._schema_errors:
            print(f"First schema error: {self._schema_errors[0]}")

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.conversations)

    def get_first_turn_pairs(self) -> List[Tuple[str, str]]:
        """Extract first user→assistant turn from each conversation.

        Returns only pairs where both user prompt and assistant response
        are non-empty after stripping whitespace.
        """
        pairs: List[Tuple[str, str]] = []
        for conversation in self.conversations:
            messages = conversation["conversation"]
            user_text, assistant_text = "", ""

            for msg in messages:
                role = msg.get("role", "")
                content = str(msg.get("content", "")).strip()
                if role == "user" and not user_text:
                    user_text = content
                elif role == "assistant" and not assistant_text:
                    assistant_text = content
                # Once we have both, stop early
                if user_text and assistant_text:
                    break

            if user_text and assistant_text:
                pairs.append((user_text, assistant_text))
        return pairs

    def get_all_turn_pairs(self) -> List[Tuple[str, str]]:
        """Extract every consecutive user→assistant pair across all turns."""
        pairs: List[Tuple[str, str]] = []
        for conversation in self.conversations:
            messages = conversation["conversation"]
            pending_user: str | None = None
            for msg in messages:
                role = msg.get("role", "")
                content = str(msg.get("content", "")).strip()
                if role == "user":
                    pending_user = content
                elif role == "assistant" and pending_user:
                    if pending_user and content:
                        pairs.append((pending_user, content))
                    pending_user = None
        return pairs

    def get_conversation_texts(self) -> List[str]:
        """Return full conversation text per sample (role-prefixed lines)."""
        texts: List[str] = []
        for conversation in self.conversations:
            lines = []
            for msg in conversation["conversation"]:
                role = msg.get("role", "unknown")
                content = str(msg.get("content", "")).strip()
                lines.append(f"{role}: {content}")
            texts.append("\n".join(lines))
        return texts

    def get_stats(self) -> dict:
        total_turns = 0
        models: dict[str, int] = {}
        languages: dict[str, int] = {}

        for conversation in self.conversations:
            total_turns += len(conversation.get("conversation", []))
            model = conversation.get("model", "unknown")
            models[model] = models.get(model, 0) + 1
            lang = conversation.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1

        return {
            "total_conversations": len(self.conversations),
            "total_turns": total_turns,
            "avg_turns_per_conversation": (
                total_turns / len(self.conversations)
                if self.conversations else 0.0
            ),
            "models": models,
            "languages": languages,
            "schema_errors": len(self._schema_errors),
        }
