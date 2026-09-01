"""Pareto validator scaffold.

This is intentionally lightweight while the Pareto implementation is under
construction. It mirrors the SCALM validator pattern but delegates the actual
frontier logic to the Pareto modules under backend/pareto/.
"""

from __future__ import annotations

from typing import Any


class ParetoValidator:
    """Placeholder validator for the Pareto-based semantic cache."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError(
            "Pareto validation is not implemented yet; add objective scoring and "
            "frontier logic in backend/pareto before wiring the runner."
        )
