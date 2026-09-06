import pytest

from backend.pareto.hypervolume import compute_hypervolume_contributions, prune_frontier_to_capacity


class TestComputeHypervolumeContributions:
    def test_matches_hand_calculated_values(self):
        points = [(-500.0, 0.1), (-300.0, 0.05), (-100.0, 0.0)]
        ref = (0.0, 1.0)

        contributions = compute_hypervolume_contributions(points, ref)

        assert contributions == pytest.approx([180.0, 190.0, 100.0])

    def test_single_point_contribution_is_full_rectangle(self):
        points = [(-10.0, 0.2)]
        ref = (0.0, 1.0)

        contributions = compute_hypervolume_contributions(points, ref)

        assert contributions == pytest.approx([10.0 * 0.8])

    def test_empty_input_returns_empty(self):
        assert compute_hypervolume_contributions([], (0.0, 1.0)) == []

    def test_reference_point_not_dominated_raises(self):
        points = [(-5.0, 0.5)]
        bad_ref = (-10.0, 1.0)  # ref x is worse (more negative) than the point's x is wrong direction

        with pytest.raises(ValueError):
            compute_hypervolume_contributions(points, bad_ref)

    def test_output_order_matches_input_order_not_sorted_order(self):
        # Deliberately pass points out of x-sorted order
        points = [(-100.0, 0.0), (-500.0, 0.1), (-300.0, 0.05)]
        ref = (0.0, 1.0)

        contributions = compute_hypervolume_contributions(points, ref)

        # Same values as the sorted test, but reordered to match this input order
        assert contributions == pytest.approx([100.0, 180.0, 190.0])


class TestPruneFrontierToCapacity:
    def test_returns_all_indices_when_capacity_sufficient(self):
        points = [(-500.0, 0.1), (-300.0, 0.05), (-100.0, 0.0)]
        kept = prune_frontier_to_capacity(points, (0.0, 1.0), capacity=5)
        assert kept == [0, 1, 2]

    def test_keeps_highest_contribution_points(self):
        points = [(-500.0, 0.1), (-300.0, 0.05), (-100.0, 0.0)]
        kept = prune_frontier_to_capacity(points, (0.0, 1.0), capacity=2)
        # contributions are [180, 190, 100] -> keep indices 0 and 1
        assert kept == [0, 1]

    def test_capacity_zero_returns_empty(self):
        points = [(-500.0, 0.1), (-300.0, 0.05)]
        kept = prune_frontier_to_capacity(points, (0.0, 1.0), capacity=0)
        assert kept == []

    def test_capacity_one_keeps_single_highest_contributor(self):
        points = [(-500.0, 0.1), (-300.0, 0.05), (-100.0, 0.0)]
        kept = prune_frontier_to_capacity(points, (0.0, 1.0), capacity=1)
        assert kept == [1]  # index 1 has the highest contribution (190)
