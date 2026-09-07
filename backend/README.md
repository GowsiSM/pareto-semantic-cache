# Backend — Implementation Details

This is the semantic-cache engine for the Pareto-optimized multi-objective
semantic cache project. It implements the SCALM baseline (clustering,
rank-based admission/eviction) plus this project's own **Pareto
multi-objective extension** (token-saving proxy vs. volatility).

> **Two objectives, not four.** The original design considered four
> objectives (token savings, latency, correctness, compute cost). What's
> actually implemented uses **two**: token-saving proxy and query
> volatility. Latency and correctness are not yet part of the objective
> function. See [`pareto/objectives.py`](pareto/objectives.py).

---

## Layout

```
backend/
├── baselines/gptcache.py            # flat-threshold GPTCache baseline (LFU/LRU)
├── cache/
│   ├── admission.py                 # RankBasedAdmissionPolicy + AlwaysAdmitPolicy
│   ├── eviction.py                  # RankSeededLFU + PlainLFU + PlainLRU
│   └── scalm_cache.py               # ScalmCache orchestrator (shared core)
├── classifier/
│   ├── domain_classifier.py         # medical/code/legal/general (word-level)
│   └── volatility_classifier.py     # STABLE/TEMPORAL/PERSONAL (word-level)
├── domain/entities.py               # CacheEntry, SemanticPattern, PatternRank
├── embedding/
│   ├── mock_embedding.py            # offline hashed bag-of-words (tests/CI)
│   ├── sentence_transformer_provider.py  # real model (network-dependent)
│   └── token_counter.py             # SimpleTokenCounter (whitespace split)
├── evaluation/metrics.py            # hit ratio, token saving, staleness, false-hit
├── experiment/
│   ├── moss_loader.py               # MOSS dataset loader
│   └── synthetic_dataset.py         # offline synthetic QA generator
├── interfaces/protocols.py          # EmbeddingProvider/VectorStore/TokenCounter
├── pareto/
│   ├── admission.py                 # JAS scalar score (secondary/cold-start signal)
│   ├── cache.py                     # ParetoCache orchestrator
│   ├── dominance.py                 # Pareto dominance + frontier
│   ├── frontier.py                  # capacity-aware frontier selection
│   ├── hypervolume.py               # hypervolume contribution + pruning
│   ├── objectives.py                # objective vector construction
│   ├── threshold.py                 # domain+volatility adaptive threshold
│   └── validator.py                 # ParetoValidator
├── scalm/
│   ├── clustering.py                # DBSCANRoundClustering
│   └── validator.py                 # SCALMValidator
├── tests/                           # 95 tests (unit + regression + e2e)
└── vector_store/
    ├── faiss_store.py               # FAISS-backed store
    └── in_memory.py                 # InMemoryVectorStore (cosine)
```

## The two objectives

`pareto/objectives.py` converts a cache candidate into a 2D
minimizing-convention vector `(-token_saving_proxy, volatility)`:

1. **Token-saving proxy** — `-total_token_count` (query + answer). Bigger
   answers save more tokens per hit, so more negative is better. This is a
   per-candidate proxy for the paper's workload-level `token_saving_ratio`
   (Eq. 4), which isn't computable at store() time.
2. **Volatility** — a keyword-based STABLE (0.0) / TEMPORAL (0.65) /
   PERSONAL (0.85) score. Lower is better (a stable answer is safer to
   cache long-term).

## How the Pareto cache decides

`pareto/cache.py` (`ParetoCache`):

- **Cold cache** (not full): admit unconditionally, matching SCALM's
  cold-start behavior.
- **Full cache**: compute the candidate's objective vector, add it to the
  existing entries' vectors, and compute the Pareto frontier. If the
  candidate is **not** in the frontier (strictly dominated by an existing
  entry in both objectives), reject it.
- If admitted: evict the entry with the **lowest hypervolume contribution**
  among dominated entries first; if no dominated entry exists, evict the
  lowest-contribution frontier member (excluding the just-admitted
  candidate).

## What's validated vs. proposed

| Component | Status |
|---|---|
| SCALM baseline (clustering, admission, eviction) | Implemented — freeze bug fixed (see `PARETO_AUDIT.md` §3) |
| GPTCache flat baseline | Implemented (rewritten from a broken exact-match version) |
| Pareto dominance, frontier, hypervolume | Implemented and tested |
| `ParetoCache` admission + eviction | Implemented |
| Volatility / domain classifiers | Implemented, bug-fixed (word-level matching) |
| Rank-volatility correlation audit | Implemented — **not yet run on real data** |
| Real-dataset validation (MOSS/LMSYS) | Requires network access |
| Latency / correctness as objectives | Not implemented |

## Running

See [`RUN.md`](RUN.md) for the exact commands to verify the test suite and
run SCALM and Pareto separately (both offline and real-data variants).

## Change log

See [`CHANGES.md`](CHANGES.md) for a per-file record of what changed in the
Pareto-extension update, and [`PARETO_AUDIT.md`](PARETO_AUDIT.md) for the
full audit of bugs found and fixed.
