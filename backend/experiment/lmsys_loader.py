"""Loader for the LMSYS-Chat-1M dataset used by the paper's audit and experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple


class LMSYSLoader:
    """Placeholder loader for the LMSYS dataset referenced throughout Section IV-VI."""

    def __init__(self, file_path: str | Path, limit: Optional[int] = None) -> None:
        self.file_path = Path(file_path)
        self.limit = limit
        self.conversations: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            print(f"LMSYS dataset not found: {self.file_path}")
            return

        with self.file_path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if self.limit is not None and index >= self.limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    import json
                    self.conversations.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    def __len__(self) -> int:
        return len(self.conversations)

    def get_first_turn_pairs(self) -> List[Tuple[str, str]]:
        """Minimal compatibility method for the MOSS-style dataset pipeline."""
        pairs: List[Tuple[str, str]] = []
        for conversation in self.conversations:
            chat = conversation.get("chat") or conversation.get("messages") or []
            if not isinstance(chat, list) or not chat:
                continue
            if len(chat) >= 2:
                user = str(chat[0].get("content") or chat[0].get("Human") or "").strip()
                assistant = str(chat[1].get("content") or chat[1].get("MOSS") or "").strip()
                if user and assistant:
                    pairs.append((user, assistant))
        return pairs

    def get_stats(self) -> dict:
        return {
            "total_conversations": len(self.conversations),
            "total_turns": sum(len(conversation.get("chat") or conversation.get("messages") or []) for conversation in self.conversations),
            "avg_turns_per_conversation": (sum(len(conversation.get("chat") or conversation.get("messages") or []) for conversation in self.conversations) / len(self.conversations)) if self.conversations else 0.0,
            "categories": {"lmsys": len(self.conversations)},
        }
