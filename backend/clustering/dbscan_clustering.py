from __future__ import annotations

import uuid
from collections import defaultdict

from sklearn.cluster import DBSCAN

from backend.domain.entities import PatternRank, SemanticPattern


class DBSCANRoundClustering:
    """
    Clusters one conversation round's embeddings using DBSCAN.

    Note on paper fidelity: Algorithm 1/2 formalize clustering as
    minimizing within-cluster sum-of-squares (Eq. 1-2), which is a
    k-means-style objective. However, section V-A states the actual
    prototype uses DBSCAN because it "shows superior performance" while
    k-means is fastest but less accurate. The paper does not reconcile
    this inconsistency between its formal objective and its implementation.
    We follow what was actually benchmarked (DBSCAN), not the stated
    objective function, and are documenting that choice explicitly rather
    than silently picking one.

    Rank assignment (top 25/50/75% -> high/mid/low) is applied by whoever
    computes token_saving_ratio downstream (Milestone 1+); this class only
    produces cluster membership + centroids.
    """

    def __init__(self, eps: float = 0.3, min_samples: int = 2) -> None:
        self.eps = eps
        self.min_samples = min_samples

    def cluster_round(
        self,
        round_index: int,
        embeddings: list[list[float]],
        entry_ids: list[str],
    ) -> list[SemanticPattern]:
        if len(embeddings) != len(entry_ids):
            raise ValueError("embeddings and entry_ids must be the same length")
        if not embeddings:
            return []

        labels = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine").fit_predict(
            embeddings
        )

        clusters: dict[int, list[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            # DBSCAN label -1 = noise point (no cluster). Each noise point
            # becomes its own singleton pattern rather than being dropped,
            # so every entry still has SOME pattern membership.
            key = label if label != -1 else f"noise-{idx}"
            clusters[key].append(idx)

        patterns: list[SemanticPattern] = []
        for member_indices in clusters.values():
            member_embeddings = [embeddings[i] for i in member_indices]
            centroid = _mean_vector(member_embeddings)
            patterns.append(
                SemanticPattern(
                    pattern_id=str(uuid.uuid4()),
                    round_index=round_index,
                    centroid=centroid,
                    member_entry_ids=[entry_ids[i] for i in member_indices],
                    rank=PatternRank.LOW,  # default; caller re-ranks after
                    # computing token_saving_ratio across all patterns.
                )
            )
        return patterns


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    dim = len(vectors[0])
    sums = [0.0] * dim
    for v in vectors:
        for i, val in enumerate(v):
            sums[i] += val
    return [s / len(vectors) for s in sums]
