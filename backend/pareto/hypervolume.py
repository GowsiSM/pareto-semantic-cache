"""
Hypervolume contribution for pruning an over-large Pareto frontier.

PROJECT-PROPOSED EXTENSION — not from the SCALM paper (which has no
Pareto/multi-objective concept at all). Hypervolume contribution is a
standard multi-objective-optimization diversity metric (see e.g. the
hypervolume indicator literature referenced alongside NSGA-II-style
approaches), applied here to a 2-objective case specifically.

PROBLEM THIS SOLVES: the Pareto frontier (non-dominated set) can still
be larger than the cache's remaining capacity -- being non-dominated
doesn't bound how many points qualify. When that happens, we need a
principled way to rank frontier points by how much unique value each
contributes, so we can prune the least valuable ones rather than
picking arbitrarily (e.g. by insertion order).

APPROACH (2D only, minimizing convention matching pareto/dominance.py):
Given a reference point R that is dominated by every point on the
frontier (i.e., worse than all of them in both objectives), each
point's hypervolume contribution is the area of objective space it
uniquely covers relative to R, that its neighbors on the frontier do
NOT already cover. For 2D, sorting the frontier by one objective makes
this a simple rectangle-area computation between consecutive points.

This implementation is intentionally 2D-only (matching the two
objectives used in pareto/objectives.py: -token_saving_proxy,
volatility). A general N-dimensional hypervolume calculation is
exponentially harder and not needed for this project's current scope.
"""
from __future__ import annotations

from typing import Sequence


def compute_hypervolume_contributions(
    frontier_points: Sequence[tuple[float, float]],
    reference_point: tuple[float, float],
) -> list[float]:
    """
    Return the hypervolume contribution of each point in frontier_points,
    in the SAME ORDER as the input list (not sorted).

    `reference_point` must be dominated by (worse than) every point in
    frontier_points in both coordinates, i.e. reference_point[i] >=
    max(p[i] for p in frontier_points) for each objective i (since lower
    is better under the minimizing convention).
    """
    n = len(frontier_points)
    if n == 0:
        return []

    ref_x, ref_y = reference_point
    for x, y in frontier_points:
        if x > ref_x or y > ref_y:
            raise ValueError(
                f"reference_point {reference_point} is not dominated by point "
                f"({x}, {y}) -- every frontier point must be <= reference_point "
                f"in both coordinates for a valid hypervolume calculation"
            )

    if n == 1:
        p = frontier_points[0]
        area = (reference_point[0] - p[0]) * (reference_point[1] - p[1])
        return [area]

    # Sort by x ascending (== y descending for a valid non-dominated frontier,
    # since no point can dominate another).
    order = sorted(range(n), key=lambda i: frontier_points[i][0])
    sorted_points = [frontier_points[i] for i in order]

    contributions_sorted: list[float] = [0.0] * n
    for rank, (x, y) in enumerate(sorted_points):
        # The "next" point (larger x, smaller-or-equal y) bounds how far
        # right this point's unique rectangle extends. For the last point
        # (largest x), it extends out to the reference point's x.
        next_x = sorted_points[rank + 1][0] if rank + 1 < n else ref_x
        width = max(0.0, next_x - x)
        height = max(0.0, ref_y - y)
        contributions_sorted[rank] = width * height

    # Map back to original input order.
    contributions = [0.0] * n
    for rank, original_index in enumerate(order):
        contributions[original_index] = contributions_sorted[rank]
    return contributions


def prune_frontier_to_capacity(
    frontier_points: Sequence[tuple[float, float]],
    reference_point: tuple[float, float],
    capacity: int,
) -> list[int]:
    """
    Given a Pareto frontier larger than `capacity`, return the indices
    (into frontier_points, original order) of the `capacity` points with
    the HIGHEST hypervolume contribution -- i.e. the points to KEEP.

    If len(frontier_points) <= capacity, returns all indices unchanged.
    """
    n = len(frontier_points)
    if capacity >= n:
        return list(range(n))
    if capacity <= 0:
        return []

    contributions = compute_hypervolume_contributions(frontier_points, reference_point)
    ranked_indices = sorted(range(n), key=lambda i: contributions[i], reverse=True)
    return sorted(ranked_indices[:capacity])
