"""GPTCache baseline used in the paper's experimental comparison.

This is intentionally minimal: it does global-threshold retrieval without the
SCALM clustering or Pareto frontier logic, matching the baseline described in
Section VI-A.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class GPTCache:
    """Simplified global-threshold cache baseline."""

    def __init__(self, similarity_threshold: float = 0.90) -> None:
        self.threshold = similarity_threshold
        self._entries: Dict[str, tuple[str, Any]] = {}

    def store(self, query: str, answer: str, metadata: Optional[dict] = None) -> None:
        self._entries[query] = (answer, metadata or {})

    def lookup(self, query: str, similarity: float | None = None) -> tuple[bool, Optional[str]]:
        if query not in self._entries:
            return False, None

        if similarity is None:
            similarity = self.threshold

        if similarity >= self.threshold:
            return True, self._entries[query][0]
        return False, None

    def __len__(self) -> int:
        return len(self._entries)
