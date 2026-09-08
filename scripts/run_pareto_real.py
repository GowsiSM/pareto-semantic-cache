# run_pareto_real.py
"""
Three-way comparison (GPTCache vs. SCALM vs. Pareto) on REAL MOSS data.

This is the real-data counterpart to scripts/run_pareto.py (which runs on
the synthetic dataset with the mock embedder). It uses:
    - the real MOSS first-turn QA pairs,
    - the real SentenceTransformer embedding provider (all-MiniLM-L6-v2),
    - the fixed SCALMValidator (real rank-based admission, not the frozen
      warmup set),
    - the ParetoValidator with the same real embedder.

The result is reported as-is, including if Pareto loses on some metric
(as it did in the synthetic run). See PARETO_DESIGN.md section 6 item 3.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.baselines.gptcache import GPTCache
from backend.classifier.volatility_classifier import VolatilityClassifier
from backend.embedding.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)
from backend.embedding.token_counter import SimpleTokenCounter
from backend.experiment.moss_loader import MOSSLoader
from backend.pareto.validator import ParetoValidator
from backend.scalm.validator import SCALMValidator
from backend.vector_store.in_memory import InMemoryVectorStore

SEPARATOR = "=" * 60

DATA_DIR = PROJECT_ROOT / "data"
DATASET_CANDIDATES = [
    DATA_DIR / "moss-sample-10k.jsonl",
    PROJECT_ROOT / "moss-sample-10k.jsonl",
]
DATASET_PATH = next(
    (path for path in DATASET_CANDIDATES if path.exists()), DATASET_CANDIDATES[0]
)

# Real-data run parameters. Keep the sample modest so the run completes
# in reasonable time with real embeddings + per-miss clustering.
SAMPLE_SIZE = 2000
CACHE_CAPACITY = 100
SIMILARITY_THRESHOLD = 0.90
WARMUP_COUNT = 100


def print_section(title: str) -> None:
    print(SEPARATOR)
    print(title)
    print(SEPARATOR)


def run_gptcache(qa_pairs, embedder, capacity: int, threshold: float) -> dict:
    """Run the flat-threshold GPTCache baseline (LFU eviction)."""
    cache = GPTCache(
        embedding_provider=embedder,
        vector_store=InMemoryVectorStore(),
        token_counter=SimpleTokenCounter(),
        capacity=capacity,
        similarity_threshold=threshold,
        eviction="lfu",
    )
    token_counter = SimpleTokenCounter()
    vol_clf = VolatilityClassifier()
    stats = {
        "hits": 0, "misses": 0,
        "tokens_saved": 0, "total_tokens": 0,
        "stale_hits": 0, "false_hits": 0,
    }

    for query, response in qa_pairs[:WARMUP_COUNT]:
        cache.store(query, response)

    for query, response in qa_pairs[WARMUP_COUNT:]:
        response_tokens = token_counter.count(response)
        stats["total_tokens"] += response_tokens
        result = cache.lookup(query)
        if result.hit:
            stats["hits"] += 1
            stats["tokens_saved"] += response_tokens
            # Quality metrics: stale if matched entry's query is volatile,
            # false if similarity below threshold (defensive).
            entry_query = getattr(result.entry, "query_text", None)
            if entry_query and vol_clf.volatility_score(entry_query) > 0.0:
                stats["stale_hits"] += 1
            if result.similarity is not None and result.similarity < threshold:
                stats["false_hits"] += 1
        else:
            stats["misses"] += 1
            cache.store(query, response)

    total = stats["hits"] + stats["misses"]
    hits = stats["hits"]
    return {
        "hit_rate": stats["hits"] / total if total else 0,
        "token_saving_rate": (
            stats["tokens_saved"] / stats["total_tokens"]
            if stats["total_tokens"] else 0
        ),
        "staleness_rate": stats["stale_hits"] / hits if hits else 0,
        "false_hit_rate": stats["false_hits"] / hits if hits else 0,
        "hits": stats["hits"],
        "misses": stats["misses"],
        "stale_hits": stats["stale_hits"],
        "false_hits": stats["false_hits"],
        "total_queries": total,
        "tokens_saved": stats["tokens_saved"],
        "total_tokens": stats["total_tokens"],
    }


def run_scalm(qa_pairs, embedder, capacity: int, threshold: float) -> dict:
    """Run SCALM with the real embedder injected."""
    validator = SCALMValidator(
        capacity=capacity,
        similarity_threshold=threshold,
        embedding_provider=embedder,
    )
    return validator.run(qa_pairs, warmup_count=WARMUP_COUNT)


def run_pareto(qa_pairs, embedder, capacity: int, threshold: float) -> dict:
    """Run the Pareto extension with the real embedder injected."""
    validator = ParetoValidator(
        capacity=capacity,
        embedding_provider=embedder,
        similarity_threshold=threshold,
    )
    return validator.run(qa_pairs, warmup_count=WARMUP_COUNT)


def print_results(name: str, results: dict) -> None:
    print(f"{name:<12} hit={results['hit_rate']:.3f}   "
          f"token_saving={results['token_saving_rate']:.3f}   "
          f"staleness={results.get('staleness_rate', 0):.3f}   "
          f"false_hit={results.get('false_hit_rate', 0):.3f}   "
          f"(hits={results['hits']}, stale={results.get('stale_hits', 0)}, "
          f"false={results.get('false_hits', 0)}, misses={results['misses']})")


def main() -> None:
    print_section("Three-Way Comparison on REAL MOSS data")

    if not DATASET_PATH.exists():
        print(f"Sample file not found. Checked: {DATASET_PATH}")
        sys.exit(1)

    print(f"Dataset: {DATASET_PATH}")
    loader = MOSSLoader(DATASET_PATH)
    qa_pairs = loader.get_first_turn_pairs()
    print(f"First-turn QA pairs available: {len(qa_pairs)}")

    qa_pairs = qa_pairs[:SAMPLE_SIZE]
    print(f"Using {len(qa_pairs)} pairs")
    print(f"Capacity: {CACHE_CAPACITY}, warmup: {WARMUP_COUNT}, "
          f"similarity_threshold: {SIMILARITY_THRESHOLD}")
    print("Embedding: SentenceTransformer (all-MiniLM-L6-v2, 384-dim)")

    embedder = SentenceTransformerEmbeddingProvider()

    print()
    print_section("Running GPTCache baseline (LFU)")
    gpt_results = run_gptcache(qa_pairs, embedder, CACHE_CAPACITY, SIMILARITY_THRESHOLD)

    print()
    print_section("Running SCALM (real embedder)")
    scalm_results = run_scalm(qa_pairs, embedder, CACHE_CAPACITY, SIMILARITY_THRESHOLD)

    print()
    print_section("Running Pareto extension (real embedder)")
    pareto_results = run_pareto(qa_pairs, embedder, CACHE_CAPACITY, SIMILARITY_THRESHOLD)

    print()
    print_section("Comparison Results (REAL MOSS data)")
    print_results("GPTCache", gpt_results)
    print_results("SCALM", scalm_results)
    print_results("Pareto", pareto_results)

    print()
    print_section("Interpretation")
    print("Reported as-is on real data. GPTCache (flat baseline) often wins")
    print("on raw hit ratio because it admits everything; Pareto is more")
    print("conservative (rejects dominated candidates), which trades raw hit")
    print("ratio for lower false-hit risk. SCALM's number reflects its real")
    print("clustering-driven rank admission (the frozen-after-warmup bug is")
    print("fixed). Staleness_rate: fraction of hits where the matched entry's")
    print("query is volatile (temporal/personal). False_hit_rate: fraction of")
    print("hits where similarity was below the configured threshold (defensive).")
    print("If Pareto loses on a metric, that is the honest result.")


if __name__ == "__main__":
    main()
