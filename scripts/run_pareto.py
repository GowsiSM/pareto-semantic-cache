# run_pareto.py
"""
Three-way comparison: GPTCache baseline vs. SCALM vs. the Pareto extension.

Runs entirely offline using the synthetic dataset + MockEmbeddingProvider,
so it works in a network-less sandbox. Mirrors run_scalm.py's structure
(sectioned output, same metric names) so the three systems can be diffed
directly.

NOTE on the SCALM result: SCALMValidator now assigns real ranks
(HIGH/MID/LOW) to post-warmup entries via clustering + token-saving-ratio
ranking, so its cache admits new entries even after warmup. The earlier
frozen-after-warmup bug is fixed. See backend/scalm/validator.py and
backend/PARETO_AUDIT.md §3 for details.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.baselines.gptcache import GPTCache
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.embedding.token_counter import SimpleTokenCounter
from backend.experiment.synthetic_dataset import generate_dataset
from backend.pareto.validator import ParetoValidator
from backend.scalm.validator import SCALMValidator
from backend.vector_store.in_memory import InMemoryVectorStore

# Synthetic-run parameters (see backend/PARETO_AUDIT.md section 5).
# The mock embedder is lexical-overlap based, so paraphrase variants score
# ~0.33-0.71 (below the paper's 0.90 threshold). We therefore use 0.60 for
# this synthetic comparison and document why -- it is NOT the paper's
# threshold, it's what makes the mock embedder's similarity scale usable.
N_QUERIES = 300
REUSE_RATE = 0.15
SEED = 42
CACHE_CAPACITY = 20
SIMILARITY_THRESHOLD = 0.60
WARMUP_COUNT = 100

SEPARATOR = "=" * 60


def print_section(title: str) -> None:
    print(SEPARATOR)
    print(title)
    print(SEPARATOR)


def run_gptcache(qa_pairs, capacity: int, threshold: float) -> dict:
    """Run the flat-threshold GPTCache baseline (LFU eviction)."""
    embedder = MockEmbeddingProvider()
    cache = GPTCache(
        embedding_provider=embedder,
        vector_store=InMemoryVectorStore(),
        token_counter=SimpleTokenCounter(),
        capacity=capacity,
        similarity_threshold=threshold,
        eviction="lfu",
    )
    token_counter = SimpleTokenCounter()
    stats = {"hits": 0, "misses": 0, "tokens_saved": 0, "total_tokens": 0}

    for query, response in qa_pairs[:WARMUP_COUNT]:
        cache.store(query, response)

    for query, response in qa_pairs[WARMUP_COUNT:]:
        response_tokens = token_counter.count(response)
        stats["total_tokens"] += response_tokens
        result = cache.lookup(query)
        if result.hit:
            stats["hits"] += 1
            stats["tokens_saved"] += response_tokens
        else:
            stats["misses"] += 1
            cache.store(query, response)

    total = stats["hits"] + stats["misses"]
    return {
        "hit_rate": stats["hits"] / total if total else 0,
        "token_saving_rate": (
            stats["tokens_saved"] / stats["total_tokens"]
            if stats["total_tokens"] else 0
        ),
        "hits": stats["hits"],
        "misses": stats["misses"],
        "total_queries": total,
        "tokens_saved": stats["tokens_saved"],
        "total_tokens": stats["total_tokens"],
    }


def run_scalm(qa_pairs, capacity: int, threshold: float) -> dict:
    """Run SCALM with the mock embedder injected (offline)."""
    validator = SCALMValidator(
        capacity=capacity,
        similarity_threshold=threshold,
        embedding_provider=MockEmbeddingProvider(),
    )
    return validator.run(qa_pairs, warmup_count=WARMUP_COUNT)


def run_pareto(qa_pairs, capacity: int, threshold: float) -> dict:
    """Run the Pareto extension (defaults to mock embedder)."""
    validator = ParetoValidator(capacity=capacity, similarity_threshold=threshold)
    return validator.run(qa_pairs, warmup_count=WARMUP_COUNT)


def print_results(name: str, results: dict) -> None:
    print(f"{name:<12} hit={results['hit_rate']:.3f}   "
          f"token_saving={results['token_saving_rate']:.3f}   "
          f"(hits={results['hits']}, misses={results['misses']})")


def main() -> None:
    print_section("Pareto Extension: Three-Way Comparison (offline synthetic)")

    qa_pairs = [
        (pair.query_text, pair.answer_text)
        for pair in generate_dataset(N_QUERIES, reuse_rate=REUSE_RATE, seed=SEED)
    ]
    print(f"Dataset: {len(qa_pairs)} queries, reuse_rate={REUSE_RATE}, seed={SEED}")
    print(f"Capacity: {CACHE_CAPACITY}, warmup: {WARMUP_COUNT}, "
          f"similarity_threshold: {SIMILARITY_THRESHOLD}")
    print(f"Embedding: MockEmbeddingProvider (offline, lexical-overlap)")

    print()
    print_section("Running GPTCache baseline (LFU)")
    gpt_results = run_gptcache(qa_pairs, CACHE_CAPACITY, SIMILARITY_THRESHOLD)

    print()
    print_section("Running SCALM (mock embedder)")
    scalm_results = run_scalm(qa_pairs, CACHE_CAPACITY, SIMILARITY_THRESHOLD)

    print()
    print_section("Running Pareto extension")
    pareto_results = run_pareto(qa_pairs, CACHE_CAPACITY, SIMILARITY_THRESHOLD)

    print()
    print_section("Comparison Results")
    print_results("GPTCache", gpt_results)
    print_results("SCALM", scalm_results)
    print_results("Pareto", pareto_results)

    print()
    print_section("Interpretation")
    print("GPTCache (flat baseline) often wins on raw hit ratio here because")
    print("it admits everything; Pareto is more conservative (rejects dominated")
    print("candidates), which trades raw hit ratio for lower false-hit risk.")
    print("SCALM's number reflects its real clustering-driven rank admission")
    print("(the earlier frozen-after-warmup bug is fixed -- see the module")
    print("docstring and backend/PARETO_AUDIT.md §3).")


if __name__ == "__main__":
    main()
