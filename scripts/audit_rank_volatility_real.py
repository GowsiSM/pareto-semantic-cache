# audit_rank_volatility_real.py
"""
Audit the rank-volatility relationship on REAL MOSS data.

This is the real-data counterpart to scripts/audit_rank_volatility.py
(which runs on the synthetic dataset with the mock embedder). It answers
the question in PARETO_DESIGN.md section 5: is there actually a conflict
between SCALM's TSR rank and this project's volatility signal on real
data?

Method (mirrors the synthetic audit):
    1. Load first-turn QA pairs from the real MOSS sample.
    2. Embed the queries with the real SentenceTransformer provider
       (all-MiniLM-L6-v2, 384-dim).
    3. DBSCAN-cluster the embeddings into semantic patterns.
    4. Per pattern: TSR proxy (total token count of member answers) and
       volatility (max VolatilityClassifier score across member queries).
    5. Compute the Spearman rank correlation between TSR and volatility.

Interpretation thresholds (PARETO_DESIGN.md section 5):
    rho < 0.3  -> premise holds (objectives independent; real trade-off)
    rho > 0.7  -> premise likely does not hold (no meaningful conflict)
    in between -> a real but modest trade-off; report the value itself.

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
from backend.embedding.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)
from backend.experiment.moss_loader import MOSSLoader
from backend.scalm.clustering import DBSCANRoundClustering

SEPARATOR = "=" * 60

DATA_DIR = PROJECT_ROOT / "data"
DATASET_CANDIDATES = [
    DATA_DIR / "moss-sample-10k.jsonl",
    PROJECT_ROOT / "moss-sample-10k.jsonl",
]
DATASET_PATH = next(
    (path for path in DATASET_CANDIDATES if path.exists()), DATASET_CANDIDATES[0]
)

# Number of first-turn pairs to embed and cluster. Keep modest so the
# script runs in reasonable time with real embeddings + DBSCAN.
SAMPLE_SIZE = 2000
# DBSCAN eps for real 384-dim embeddings. The synthetic audit used 0.3 on
# mock embeddings; real MiniLM embeddings are denser, so use a larger eps.
DBSCAN_EPS = 0.6
DBSCAN_MIN_SAMPLES = 2


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
    print("Rank-Volatility Audit (REAL MOSS data)")
    print(SEPARATOR)

    if not DATASET_PATH.exists():
        print(f"Sample file not found. Checked: {DATASET_PATH}")
        sys.exit(1)

    print(f"Dataset: {DATASET_PATH}")
    loader = MOSSLoader(DATASET_PATH)
    qa_pairs = loader.get_first_turn_pairs()
    print(f"First-turn QA pairs available: {len(qa_pairs)}")

    qa_pairs = qa_pairs[:SAMPLE_SIZE]
    print(f"Using {len(qa_pairs)} pairs for the audit")

    if len(qa_pairs) < 2:
        print("Not enough pairs to compute a meaningful correlation.")
        return

    print("\nEmbedding queries with SentenceTransformer (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformerEmbeddingProvider()
    embeddings = [embedder.embed(pair[0]) for pair in qa_pairs]
    entry_ids = [f"e{i}" for i in range(len(qa_pairs))]
    print(f"Embedded {len(embeddings)} queries (dim={len(embeddings[0])})")

    print(f"\nClustering with DBSCAN (eps={DBSCAN_EPS}, min_samples={DBSCAN_MIN_SAMPLES})...")
    clustering = DBSCANRoundClustering(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
    patterns = clustering.cluster_round(1, embeddings, entry_ids)
    print(f"Clusters formed: {len(patterns)}")

    if len(patterns) < 2:
        print("Not enough clusters to compute a meaningful correlation.")
        return

    classifier = VolatilityClassifier()
    tsr_values: list[float] = []
    volatility_values: list[float] = []

    for pattern in patterns:
        member_ids = set(pattern.member_entry_ids)
        member_queries = [
            pair[0] for i, pair in enumerate(qa_pairs) if entry_ids[i] in member_ids
        ]
        if not member_queries:
            continue
        # TSR proxy: total token count of member answers (higher = more
        # tokens saved by caching this pattern).
        total_tokens = sum(
            len(pair[1].split()) for i, pair in enumerate(qa_pairs)
            if entry_ids[i] in member_ids
        )
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
    print("Interpretation (PARETO_DESIGN.md section 5):")
    if rho < -0.3:
        print("  Negative correlation: high-TSR patterns tend to be volatile.")
        print("  Supports the Pareto extension's premise -- a single-objective")
        print("  cache that maximizes token savings alone would over-cache")
        print("  volatile content.")
    elif rho > 0.7:
        print("  Strong positive correlation: high-TSR patterns tend to be stable.")
        print("  The honest finding is 'no meaningful conflict found in practice'")
        print("  -- a legitimate, reportable negative result, not a failure of")
        print("  the implementation.")
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
