"""Pareto frontier helpers."""

from __future__ import annotations

from typing import Iterable, Sequence

from backend.pareto.dominance import pareto_frontier


def select_frontier(objectives: Iterable[Sequence[float]]) -> list[Sequence[float]]:
    """Return the Pareto-optimal frontier for the given objective vectors."""
    return pareto_frontier(objectives)
