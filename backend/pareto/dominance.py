"""Utilities for Pareto-dominance checks and objective comparisons."""

from __future__ import annotations

from typing import Iterable, Sequence


def dominates(left: Sequence[float], right: Sequence[float]) -> bool:
    """Return True when left is at least as good as right in every objective.

    The convention used here is minimizing objectives, so lower values are
    preferred. This is a lightweight placeholder for the Pareto implementation
    that is expected to grow as the algorithm develops.
    """
    if len(left) != len(right):
        raise ValueError("left and right objectives must have the same length")

    better_or_equal = all(a <= b for a, b in zip(left, right))
    strictly_better = any(a < b for a, b in zip(left, right))
    return better_or_equal and strictly_better


def pareto_frontier(objectives: Iterable[Sequence[float]]) -> list[Sequence[float]]:
    """Return the non-dominated points from an iterable of objective vectors."""
    points = list(objectives)
    frontier: list[Sequence[float]] = []
    for candidate in points:
        if not any(dominates(other, candidate) for other in points if other is not candidate):
            frontier.append(candidate)
    return frontier
