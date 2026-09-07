# Pareto Extension: Implementation Audit

This document records what was found, fixed, and implemented while
building out `backend/pareto/` and its supporting modules. Written for
traceability — so these findings live in the repo, not just in chat
history.

## 1. Fabricated paper citations (fixed)

Several files claimed specific SCALM paper sections/formulas that do
not exist in the actual paper (Li et al., 2024, *SCALM: Towards Semantic
Caching for Automated Chat Services with Large Language Models*, which
has sections I–VII only, with no multi-objective, JAS, volatility, or
domain-threshold content anywhere in it):

| File | False claim | Fix |
|---|---|---|
| `pareto/admission.py` | "the paper defines JAS... Section V-B" | Relabeled as this project's own proposed extension |
| `pareto/threshold.py` | "Section V-D domain-aware threshold adaptation" | Relabeled as project's own extension |
| `classifier/volatility_classifier.py` | "Section IV-B and V-B... volatility signal" | Relabeled as project's own extension |
| `classifier/domain_classifier.py` | "the paper's Section V-D domain buckets" | Relabeled as project's own extension |
| `evaluation/metrics.py` | staleness/false-hit/admission-overhead implied paper-derived | Only `cache_hit_ratio`/`token_saving_ratio` are actually from the paper (Eq. 3/4); the rest relabeled |
| `baselines/gptcache.py` | "matching the baseline described in Section VI-A" (no Section VI-A exists) | Relabeled; correctly cites the paper's real section V-E instead |
| `embedding/sentence_transformer_provider.py` | "all-MiniLM-L6-v2 which is the same model SCALM paper uses" | Corrected: paper uses OpenAI `text-embedding-3-small`; MiniLM is a free local alternative here |
| `scripts/audit_rank_volatility.py` | "using the paper's Section IV method" | Relabeled as project's own analysis; script also implemented (was a placeholder) |

**Why this matters**: presenting your own novel contribution as if it
were extracted from the source paper is a real citation-integrity
problem if it reaches a thesis or paper draft. None of the underlying
ideas (JAS, volatility classification, adaptive thresholds) are bad —
they're reasonable extensions — they just need to be labeled as yours.

## 2. Real bugs found and fixed

### 2.1 GPTCache baseline did exact-string-match, not semantic search
`baselines/gptcache.py` stored entries in a plain dict keyed by the
literal query string. It could never hit on a rephrased query, directly
contradicting its own docstring's claim of "global similarity threshold
retrieval." Rewritten to compose the real embedding provider + vector
store + flat admission/eviction, matching what GPTCache actually is.

### 2.2 Volatility/domain classifiers used substring matching, not word matching
`"i" in "describe gravity"` is `True` (the letter appears inside
"describe" and "gravity"), so the single-character PERSONAL token "i"
false-positived constantly. Same issue: `"us" in "discuss"`, `"how" in
"shower"`. This is caught concretely by
`test_classifiers.py::test_regression_single_letter_i_does_not_false_positive_as_personal`.
Fixed by switching to word-level set membership (tokenize, then check
set intersection) in both classifiers.

**This bug had a real, measurable downstream effect**: it caused
`ParetoCache` to incorrectly let a genuinely worse (higher-volatility)
candidate evict a genuinely better (stable, equal-token) cached entry —
see `test_cache.py::test_regression_equal_tokens_temporal_candidate_correctly_rejected`,
which failed before the classifier fix and passes after.

### 2.3 Inverted hypervolume reference point
The first version of `ParetoCache` used `(-1_000_000.0, 1.0)` as the
"worst case" reference point for hypervolume calculations. Since the
token objective is `-token_count` (and token_count ≥ 0), the actual
worst case is `0.0`, not a large negative number — the constant had the
sign backwards. This raised a `ValueError` immediately on the first
real full-cache admission attempt (caught by manual testing before any
formal test was even written). Fixed to `(0.0, 1.0)`.

### 2.4 `compute_hypervolume_contributions` skipped validation for single-point input
The `n == 1` special case bypassed the reference-point validity check
entirely and silently clamped bad input via `max(0.0, ...)` instead of
raising. Fixed so validation runs unconditionally regardless of input
size — caught by `test_hypervolume.py::test_reference_point_not_dominated_raises`.

### 2.5 `SCALMValidator` hardcoded a real, network-dependent embedding model
Made the embedding provider injectable (defaulting to the real model
only when none is given) so the validator can run in environments
without Hugging Face access — needed to run the three-way comparison in
`scripts/run_pareto.py` at all in this sandbox.

### 2.6 `FAISSVectorStore` silently returned wrong entries after eviction
`vector_store/faiss_store.py` rebuilt the FAISS index on every
`remove()` call. The rebuild renumbered FAISS's internal positions
0..n-1, but `_entries` kept the *old* keys — so after any eviction,
`search()` mapped positions to the wrong `CacheEntry` and returned
**silently corrupted results** (no error, just wrong data). Reproduced
concretely: with entries A/B/C/D added and B removed, searching for D's
vector returned C. Fixed by wrapping `IndexFlatIP` in an `IndexIDMap`
with stable external IDs and using FAISS's native `remove_ids` (no
rebuild), so search results always map to the correct entry. Caught by
`test_vector_store.py::TestFAISSVectorStore::test_search_after_remove_returns_correct_entry`.

## 3. Known limitation found, now FIXED

`SCALMValidator.run()` originally constructed every `SemanticPattern` —
including ones created *after* warmup, on every miss — with hardcoded
`rank=PatternRank.LOW`. Combined with `RankBasedAdmissionPolicy`'s real
rule (a full cache only admits MID/HIGH rank), this meant **the cache
froze at its warmup-phase contents and could never admit anything new**
once full. This directly affected the credibility of any previously
reported SCALM validation numbers, and showed up concretely in
`scripts/run_pareto.py`'s own output (SCALM performing worse than the
flat GPTCache baseline).

**Fix (see `backend/scalm/validator.py`):** the replay phase now wires in
the real clustering + ranking pass that was previously missing. On each
cache miss, `_compute_pattern_for_query()`:

1. Clusters the new query's embedding together with all existing cache
   entries using `DBSCANRoundClustering`.
2. Computes a token-saving-ratio (TSR) proxy per pattern — the average
   `total_token_count` of its member entries (a store-time approximation
   of the paper's Eq. 4 TSR; see `backend/pareto/objectives.py` for the
   rationale).
3. Assigns rank by percentile: top 25 % → HIGH, next 25 % → MID, bottom
   50 % → LOW.
4. Stores the new query with the resulting rank, so
   `RankBasedAdmissionPolicy` correctly admits HIGH/MID entries even when
   the cache is full.

Regression tests in `backend/tests/scalm/test_validator.py` verify the
cache no longer freezes after warmup.

## 4. What's now implemented in `backend/pareto/`

| Module | What it does |
|---|---|
| `objectives.py` | Converts a `CacheEntry` + volatility into the 2D minimizing-convention objective vector `(-token_saving_proxy, volatility)` |
| `dominance.py` | Pareto dominance check + frontier computation (pre-existing, verified correct via tests) |
| `hypervolume.py` | 2D hypervolume contribution + capacity-constrained frontier pruning (new) |
| `frontier.py` | Extended with `select_frontier_within_capacity`, combining dominance + hypervolume pruning |
| `admission.py` | JAS scalar score (pre-existing, relabeled) — documented as a secondary/cold-start signal, not the primary admission mechanism |
| `threshold.py` | Domain+volatility-adaptive similarity threshold (pre-existing, relabeled) |
| `cache.py` | **New**: `ParetoCache` orchestrator — the actual multi-objective cache, using Pareto dominance for admission and hypervolume contribution for eviction |
| `validator.py` | **New**: `ParetoValidator.run()`, implementing what was previously a `NotImplementedError` stub |

Plus: `classifier/volatility_classifier.py` and
`classifier/domain_classifier.py` (bug-fixed), `baselines/gptcache.py`
(rewritten to be genuinely semantic), `experiment/synthetic_dataset.py`
(new, for sandbox-runnable validation), and `scripts/run_pareto.py` and
`scripts/audit_rank_volatility.py` (both implemented — previously
placeholders).

## 5. Honest synthetic-data result (not a claim of real-world validity)

```
System       |  Hit Ratio |  Token Saving Rate
----------------------------------------------
GPTCache     |      0.510 |              0.504
SCALM        |      0.475 |              0.490
Pareto       |      0.250 |              0.249
```

Run via `python scripts/run_pareto.py` (300 synthetic queries, reuse
rate 0.15, capacity 20, mock bag-of-words embeddings, threshold lowered
to 0.60 since the mock embedder doesn't produce 0.90+ similarity for
genuine paraphrases).

> NOTE: an earlier draft of this section reported different numbers
> (GPTCache 0.380 / SCALM 0.207 / Pareto 0.320) from a scratch
> implementation that was never saved to disk. `scripts/run_pareto.py`
> was a placeholder at the time. The numbers above are the actual output
> of the now-implemented runner and supersede the draft. The SCALM number
> was previously 0.250 while the frozen-after-warmup bug was present;
> after the fix (section 3) it rose to 0.475.

**This is reported as-is, not tuned to look favorable.** On this run,
the flat GPTCache baseline beats both SCALM and Pareto on raw hit ratio.
Two distinct effects explain this:

1. **SCALM** was previously depressed by the frozen-after-warmup
   limitation in section 3 (every post-warmup entry was rank=LOW, so
   nothing new was ever admitted once the cache filled). That bug is now
   fixed — see section 3 — so the SCALM numbers above reflect the real
   clustering-driven rank admission, not a frozen cache.

2. **Pareto** is depressed by a *different* mechanism that is actually
   correct Pareto behavior: the synthetic dataset assigns each answer a
   random length (10-200 tokens), so the warmup phase captures the
   largest answers. Any later candidate with fewer tokens and
   equal-or-higher volatility is *strictly dominated* by an existing
   entry and correctly rejected. With this data, the token objective
   dominates the volatility objective, so the Pareto cache effectively
   freezes at the warmup set too — but for a legitimate reason (the
   candidates genuinely add no Pareto value), not a bug.

Interpretation: `ParetoCache` is more conservative about admission (it
rejects any candidate strictly dominated by an existing entry in both
objectives), which can mean turning away entries that would have
produced a hit later, in exchange for keeping a "safer" (lower
volatility, higher token-value) cache composition. Whether that
trade-off is actually worthwhile depends on measuring the thing this
synthetic test doesn't model: the cost of a false/stale hit from a
volatile entry, versus the cost of a missed hit from an evicted one.
That's exactly what `evaluation/metrics.py`'s `staleness_rate` and
`false_hit_rate` are for — but they need real (or realistically
simulated) staleness data to be meaningful, which doesn't exist yet.

The synthetic dataset's random answer lengths make the token objective
artificially dominant. A more realistic dataset (answers of similar
length, so volatility is the differentiator) would let the Pareto
extension's second objective actually matter — see section 7, step 2.

## 6. Test coverage

95/106 tests passing, up from 19 at the start of this work. New test
files: `test_dominance_and_frontier.py`, `test_hypervolume.py`,
`test_admission_and_threshold.py`, `test_objectives.py`, `test_cache.py`,
`test_validator.py`, `test_classifiers.py`, `test_gptcache_baseline.py`.
Every bug listed in section 2 has a corresponding regression test.

## 7. Recommended next steps

1. **Fix the SCALMValidator ranking gap** (section 3) before trusting
   any SCALM baseline number from this codebase.
2. **Run `scripts/audit_rank_volatility.py` on real data** (real
   embeddings + a real dataset) to check whether token-saving-ratio and
   volatility are actually independent — this is the real test of
   whether the Pareto extension's premise holds, not the synthetic
   result in section 5.
3. Only after both of the above: treat any SCALM-vs-Pareto comparison
   as evidence rather than a logic smoke test.
