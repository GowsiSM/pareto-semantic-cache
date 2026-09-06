from backend.pareto.dominance import dominates, pareto_frontier
from backend.pareto.frontier import select_frontier, select_frontier_within_capacity


class TestDominates:
    def test_strictly_better_in_both_dominates(self):
        assert dominates((1.0, 1.0), (2.0, 2.0)) is True

    def test_equal_points_do_not_dominate(self):
        assert dominates((1.0, 1.0), (1.0, 1.0)) is False

    def test_better_in_one_worse_in_other_does_not_dominate(self):
        assert dominates((1.0, 5.0), (2.0, 1.0)) is False

    def test_equal_in_one_better_in_other_dominates(self):
        assert dominates((1.0, 1.0), (1.0, 2.0)) is True

    def test_mismatched_length_raises(self):
        import pytest

        with pytest.raises(ValueError):
            dominates((1.0, 2.0), (1.0,))


class TestParetoFrontier:
    def test_single_point_is_its_own_frontier(self):
        assert pareto_frontier([(1.0, 1.0)]) == [(1.0, 1.0)]

    def test_dominated_point_excluded(self):
        points = [(1.0, 1.0), (2.0, 2.0)]  # second dominated by first
        frontier = pareto_frontier(points)
        assert frontier == [(1.0, 1.0)]

    def test_mutually_non_dominated_points_both_kept(self):
        points = [(1.0, 5.0), (5.0, 1.0)]  # trade-off, neither dominates
        frontier = pareto_frontier(points)
        assert set(frontier) == {(1.0, 5.0), (5.0, 1.0)}

    def test_empty_input_returns_empty(self):
        assert pareto_frontier([]) == []


class TestSelectFrontierWithinCapacity:
    def test_all_frontier_points_kept_when_capacity_allows(self):
        objs = [(1.0, 5.0), (5.0, 1.0), (10.0, 10.0)]  # third is dominated
        kept = select_frontier_within_capacity(objs, reference_point=(20.0, 20.0), capacity=5)
        assert set(kept) == {0, 1}

    def test_dominated_points_never_kept_even_with_spare_capacity(self):
        objs = [(1.0, 1.0), (5.0, 5.0)]  # second strictly dominated
        kept = select_frontier_within_capacity(objs, reference_point=(10.0, 10.0), capacity=10)
        assert kept == [0]

    def test_frontier_larger_than_capacity_prunes_by_hypervolume(self):
        # All three mutually non-dominated (a proper trade-off curve)
        objs = [(-500.0, 0.1), (-300.0, 0.05), (-100.0, 0.0)]
        kept = select_frontier_within_capacity(objs, reference_point=(0.0, 1.0), capacity=2)
        assert len(kept) == 2
        # from the earlier hand-verified hypervolume test: middle point
        # has highest individual contribution (190), first is 180, last
        # is 100 -- so index 2 (last, weakest) should be dropped.
        assert 2 not in kept
