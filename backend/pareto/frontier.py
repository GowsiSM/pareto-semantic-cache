"""Pareto frontier helpers."""

from __future__ import annotations

from typing import Iterable, Sequence

from backend.pareto.dominance import pareto_frontier
from backend.pareto.hypervolume import prune_frontier_to_capacity


def select_frontier(objectives: Iterable[Sequence[float]]) -> list[Sequence[float]]:
    """Return the Pareto-optimal frontier for the given objective vectors."""
    return pareto_frontier(objectives)


def select_frontier_within_capacity(
    objectives: Sequence[tuple[float, float]],
    reference_point: tuple[float, float],
    capacity: int,
) -> list[int]:
    """
    Return the indices (into `objectives`) to KEEP, respecting `capacity`.

    Two-step process:
      1. Compute the non-dominated frontier.
      2. If the frontier itself exceeds `capacity`, prune it further using
         hypervolume contribution (keep the highest-contributing points).

    Dominated (non-frontier) points are never kept, even if there's
    capacity to spare — being dominated in BOTH objectives by another
    entry means there's no scenario where keeping it is better, so we
    don't need a tie-break for those.
    """
    frontier_values = pareto_frontier(objectives)
    frontier_indices = [i for i, obj in enumerate(objectives) if obj in frontier_values]
    # NOTE: `in` comparison above assumes no two distinct candidates share
    # an identical objective vector; see test_frontier.py for the
    # documented behavior when duplicates exist.

    if len(frontier_indices) <= capacity:
        return frontier_indices

    frontier_points = [objectives[i] for i in frontier_indices]
    kept_within_frontier = prune_frontier_to_capacity(frontier_points, reference_point, capacity)
    return [frontier_indices[i] for i in kept_within_frontier]
