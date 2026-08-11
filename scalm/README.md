# SCALM — Milestone 0

In-memory, dependency-light reimplementation of the core algorithmic
pieces from *SCALM: Towards Semantic Caching for Automated Chat Services
with Large Language Models* (Li et al., 2024).

## What's implemented

| Component | File | Paper fidelity |
|---|---|---|
| Cache entry / pattern domain model | `domain/entities.py` | (C) engineering interpretation of paper concepts |
| Cosine similarity vector search | `vector_store/in_memory.py` | (A) directly matches paper's search mechanism |
| DBSCAN round clustering | `clustering/dbscan_clustering.py` | (A/B) matches the *actual prototype* (section V-A), not the k-means-style objective stated in Eq. 1-2 — see docstring for the discrepancy |
| Rank-based admission (cold vs. full cache) | `cache/admission.py` | (A) directly from section IV-B |
| Rank-seeded LFU eviction | `cache/eviction.py` | (A) directly from section IV-C |
| Orchestrator | `cache/scalm_cache.py` | (C) our wiring; not in the paper |
| Mock embedding provider | `embedding/mock_embedding.py` | not in paper — test infrastructure only |

Similarity threshold defaults to **0.90**, matching the paper's Table I
finding. Tests use a lower threshold (0.80) because `MockEmbeddingProvider`
is bag-of-words, not a real semantic model — see its docstring.

## Explicitly NOT implemented yet (do not assume otherwise)

- Pattern rank computation from real token-saving-ratio data (needs a
  batch clustering pass across a full dataset, not single-insert). SE-HSC
  pruning (`Ts`/`Te` thresholds) is not implemented — only CO-HSC-style
  clustering exists so far.
- Real embedding model integration (OpenAI/local). `MockEmbeddingProvider`
  is lexical-only and explicitly unsuitable for reproducing the paper's
  reported hit-ratio numbers.
- Any persistence (Postgres/Redis/vector DB) — everything is in-memory.
- Cache safety / multi-tenant identity (model, system prompt, tenant) —
  the paper doesn't address this; it's a planned extension, not yet built.
- Request coalescing / stampede protection.
- Token saving ratio metric computation (`R_ts`, Eq. 4) — token counts
  exist on `CacheEntry` but nothing aggregates them into the metric yet.
- Any optimization-policy alternatives (weighted score, Pareto,
  probabilistic, bandits) — Milestone 0 is the faithful baseline only,
  per the roadmap's own instruction not to optimize before measuring.

## Known limitations discovered during testing (documented, not hidden)

- `MockEmbeddingProvider` at low dimensionality (<512) produces hash
  collisions between unrelated words, creating spurious similarity. Fixed
  by defaulting to 512 dims — but this is a property of the *mock*, not
  a general embedding issue, and won't apply once a real model is used.
- The paper's admission policy (full cache admits mid/high rank only)
  means an entirely unranked candidate (`pattern=None`) is never admitted
  once the cache is full. This is correct per the paper but means every
  caller needs a real clustering pass upstream before storing — there is
  no "unranked queries always get in eventually" path. Worth deciding
  explicitly in Milestone 1 how newly-seen queries get an initial pattern
  before a full clustering pass has run.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

19/19 tests passing as of this milestone.

## Next milestone (proposed, not started)

**Milestone 1**: batch CO-HSC pipeline over a small real dataset slice
(a few hundred conversations from LMSYS or MOSS), producing real
token-saving-ratio-based pattern ranks, plus a real embedding provider
(text-embedding-3-small or a local sentence-transformer) so we can
measure actual hit ratio / token saving ratio against a naive
exact-match baseline — the first point where we have real numbers to
compare optimization policies against, rather than synthetic test data.
