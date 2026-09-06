# audit_rank_volatility.py
"""
Audit the rank-volatility relationship that motivates the Pareto extension.

The SCALM paper's Section IV method ranks semantic patterns by
token-saving-ratio (TSR) and clusters by volatility. The Pareto extension
hypothesizes that a pattern's TSR rank and its volatility are in tension:
high-TSR (worth caching) patterns can also be high-volatility (risky to
cache long-term). This script measures that tension directly.

It runs OFFLINE on the synthetic dataset: DBSCAN clusters the mock
embeddings into patterns, each pattern gets a TSR rank (by total token
count) and a volatility score (via VolatilityClassifier), then we compute
the Spearman rank correlation between the two. A negative rho supports the
Pareto extension's premise (high-TSR patterns tend to be volatile).

This is an analysis workflow, not a reusable backend component, so it
lives in scripts/ rather than backend/.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.classifier.volatility_classifier import VolatilityClassifier
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.experiment.synthetic_dataset import generate_dataset
from backend.scalm.clustering import DBSCANRoundClustering

SEPARATOR = "=" * 60


def spearman_rho(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation between two equal-length sequences."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        rank = [0.0] * len(values)
        for pos, idx in enumerate(order):
            rank[idx] = pos + 1
        # Average ranks for ties
        i = 0
        while i < len(values):
            j = i
            while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
                j += 1
            if j > i:
                avg = (i + 1 + j + 1) / 2.0
                for k in range(i, j + 1):
                    rank[order[k]] = avg
            i = j + 1
        return rank

    rx = ranks(x)
    ry = ranks(y)
    n = len(x)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    cov = sum((rx[i] - mean_x) * (ry[i] - mean_y) for i in range(n))
    var_x = sum((rx[i] - mean_x) ** 2 for i in range(n))
    var_y = sum((ry[i] - mean_y) ** 2 for i in range(n))
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / ((var_x * var_y) ** 0.5)


def main() -> None:
    print(SEPARATOR)
    print("Rank-Volatility Audit (Section IV method, offline synthetic)")
    print(SEPARATOR)

    # Build a synthetic dataset with enough reuse to form clusters.
    dataset = generate_dataset(400, reuse_rate=0.30, seed=7)
    print(f"Dataset: {len(dataset)} queries")

    embedder = MockEmbeddingProvider()
    embeddings = [embedder.embed(pair.query_text) for pair in dataset]
    entry_ids = [f"e{i}" for i in range(len(dataset))]

    # Cluster into semantic patterns (DBSCAN, as the paper's prototype uses).
    clustering = DBSCANRoundClustering(eps=0.3, min_samples=2)
    patterns = clustering.cluster_round(1, embeddings, entry_ids)
    print(f"Clusters formed: {len(patterns)}")

    if len(patterns) < 2:
        print("Not enough clusters to compute a meaningful correlation.")
        return

    # For each pattern: TSR proxy (total token count of its members) and
    # volatility (max volatility score across member queries).
    classifier = VolatilityClassifier()
    tsr_values: list[float] = []
    volatility_values: list[float] = []

    for pattern in patterns:
        member_ids = set(pattern.member_entry_ids)
        member_queries = [
            pair.query_text for i, pair in enumerate(dataset)
            if entry_ids[i] in member_ids
        ]
        if not member_queries:
            continue
        # TSR proxy: total token count of member answers (higher = more
        # tokens saved by caching this pattern).
        total_tokens = sum(len(pair.answer_text.split()) for i, pair in enumerate(dataset)
                           if entry_ids[i] in member_ids)
        # Volatility: max score across members (a pattern is as volatile
        # as its most volatile member).
        vol = max(classifier.volatility_score(q) for q in member_queries)
        tsr_values.append(float(total_tokens))
        volatility_values.append(vol)

    if len(tsr_values) < 2:
        print("Not enough patterns with members to compute correlation.")
        return

    rho = spearman_rho(tsr_values, volatility_values)

    print()
    print(f"Patterns analyzed: {len(tsr_values)}")
    print(f"Spearman rho (TSR rank vs. volatility): {rho:.3f}")
    print()
    print("Interpretation:")
    if rho < -0.3:
        print("  Negative correlation: high-TSR patterns tend to be volatile.")
        print("  Supports the Pareto extension's premise -- a single-objective")
        print("  cache that maximizes token savings alone would over-cache")
        print("  volatile content.")
    elif rho > 0.3:
        print("  Positive correlation: high-TSR patterns tend to be stable.")
        print("  The two objectives align here; Pareto's benefit is less clear")
        print("  on this dataset.")
    else:
        print("  Weak correlation: TSR and volatility are largely independent")
        print("  on this dataset, so a multi-objective frontier is meaningful")
        print("  (neither objective dominates the other).")


if __name__ == "__main__":
    main()
