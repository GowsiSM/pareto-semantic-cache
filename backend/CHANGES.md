# CHANGES.md — Per-File Record of the Pareto-Extension Update

This is a complete, per-file record of every change made in the
Pareto-extension update. It complements [`PARETO_AUDIT.md`](PARETO_AUDIT.md)
(which records *why* — the bugs and citation fixes) and [`RUN.md`](RUN.md)
(which records *how to run*). This file records *what changed in each file*.

Legend:
- **NEW** — file created in this update
- **FIX** — bug fix
- **CITE** — fabricated-citation correction
- **IMPL** — implemented a previously-placeholder stub
- **REF** — refactor / structural change

---

## New Pareto modules (`backend/pareto/`)

| File | Type | Change |
|---|---|---|
| [`pareto/cache.py`](pareto/cache.py) | **NEW** | `ParetoCache` orchestrator: cold-cache unconditional admission; full-cache Pareto-dominance admission (reject dominated candidates); hypervolume-contribution eviction. Added `similarity_threshold` param (default 0.90) forwarded to the adaptive threshold adapter so the synthetic runner can use 0.60. |
| [`pareto/hypervolume.py`](pareto/hypervolume.py) | **NEW** | 2D hypervolume contribution + `prune_frontier_to_capacity`. Validates the reference point unconditionally (fixes the skipped-validation bug). |
| [`pareto/objectives.py`](pareto/objectives.py) | **NEW** | `objective_vector(entry, volatility) = (-token_saving_proxy, volatility)` under the minimizing convention. |
| [`pareto/validator.py`](pareto/validator.py) | **IMPL** | `ParetoValidator.run()` — was a `NotImplementedError` stub; now implements warmup + replay, mirroring `SCALMValidator`. Defaults to `MockEmbeddingProvider`. Added `similarity_threshold` param. |

## Pareto modules modified

| File | Type | Change |
|---|---|---|
| [`pareto/admission.py`](pareto/admission.py) | **CITE + REMOVED** | Removed false "Section V-B defines JAS" citation; relabeled JAS as this project's own extension. **File later deleted entirely**: `JointAdmissionScore` was dead code (never called by `ParetoCache`) and its weighted-sum formula contradicted the multi-objective premise. Cold-start admission is unconditional by design — see `PARETO_DESIGN.md` §4. |
| [`pareto/threshold.py`](pareto/threshold.py) | **CITE** | Removed false "Section V-D domain-aware threshold adaptation" citation; relabeled as project's own extension. |
| [`pareto/frontier.py`](pareto/frontier.py) | **IMPL** | Added `select_frontier_within_capacity` (dominance + hypervolume pruning). |

## Classifiers (bug fixes)

| File | Type | Change |
|---|---|---|
| [`classifier/volatility_classifier.py`](classifier/volatility_classifier.py) | **FIX + CITE** | Fixed substring-matching bug (`"i" in "describe gravity"` → false PERSONAL). Now uses word-level set membership. Removed false "Section IV-B/V-B" citation. |
| [`classifier/domain_classifier.py`](classifier/domain_classifier.py) | **FIX + CITE** | Same substring-matching bug fixed (`"how" in "shower"`). Now word-level. Removed false "Section V-D" citation. |

## Baselines

| File | Type | Change |
|---|---|---|
| [`baselines/gptcache.py`](baselines/gptcache.py) | **FIX + CITE** | Rewritten from a broken exact-string-match dict to a real semantic cache (composes `ScalmCache` + `AlwaysAdmitPolicy` + `PlainLFU`/`PlainLRU`). Removed false "Section VI-A" citation; correctly cites the paper's real section V-E. |
| [`baselines/__init__.py`](baselines/__init__.py) | **CITE** | Removed fabricated "Section VI" reference from the module docstring. |

## Cache core

| File | Type | Change |
|---|---|---|
| [`cache/admission.py`](cache/admission.py) | **IMPL** | Added `AlwaysAdmitPolicy` (GPTCache baseline admission). |
| [`cache/eviction.py`](cache/eviction.py) | **IMPL** | Added `PlainLFUEviction` and `PlainLRUEviction` (GPTCache baseline eviction). |

## Vector store

| File | Type | Change |
|---|---|---|
| [`vector_store/faiss_store.py`](vector_store/faiss_store.py) | **FIX** | **Fixed silent data-corruption bug**: the old implementation rebuilt the FAISS index on every `remove()`, renumbering FAISS's internal positions 0..n-1 while `_entries` kept the old keys — so after any eviction, `search()` silently returned the wrong entry. Now wraps `IndexFlatIP` in an `IndexIDMap` with stable external IDs and uses FAISS's native `remove_ids` (no rebuild), so search results always map to the correct entry. |

## Embedding

| File | Type | Change |
|---|---|---|
| [`embedding/sentence_transformer_provider.py`](embedding/sentence_transformer_provider.py) | **CITE** | Corrected false claim that the paper uses `all-MiniLM-L6-v2`; the paper uses OpenAI `text-embedding-3-small`. MiniLM is a free local alternative here. |
| [`embedding/mock_embedding.py`](embedding/mock_embedding.py) | **NEW** | Offline hashed bag-of-words embedder (512-dim, stopword-filtered, L2-normalized) for tests/CI. |

## Evaluation

| File | Type | Change |
|---|---|---|
| [`evaluation/metrics.py`](evaluation/metrics.py) | **CITE** | Clarified that only `cache_hit_ratio`/`token_saving_ratio` are from the paper (Eq. 3/4); `staleness_rate`/`false_hit_rate`/`admission_overhead` are this project's own additions. Also removed a leftover fabricated "Section VI" reference from the `compute_metrics` docstring. |

## SCALM validator

| File | Type | Change |
|---|---|---|
| [`scalm/validator.py`](scalm/validator.py) | **REF** | Made `embedding_provider` injectable (defaults to the real model only when none given) so it runs offline. **FIXED the frozen-after-warmup bug**: the replay phase now clusters each miss with existing entries via `DBSCANRoundClustering`, computes a TSR proxy per pattern, and assigns rank (HIGH/MID/LOW) by percentile, so the cache admits new entries after warmup. |

## Experiment / data

| File | Type | Change |
|---|---|---|
| [`experiment/synthetic_dataset.py`](experiment/synthetic_dataset.py) | **NEW** | Offline synthetic QA generator (8 topics, 4 stable + 4 volatile, controlled reuse rate) for sandbox-runnable validation. |
| [`experiment/lmsys_loader.py`](experiment/lmsys_loader.py) | **FIX** | **Fixed wrong-schema guessing**: the loader previously assumed a MOSS-style schema (`chat`/`messages` with `Human`/`MOSS` keys). The real LMSYS-Chat-1M schema uses an OpenAI chat format — a top-level `conversation` list of messages with `role`/`content` keys (plus `model`, `turn`, `language`, `openai_moderation`, `redacted`). Now validates the schema on load (skips and reports malformed rows), extracts first-turn and all-turn QA pairs from `role`/`content`, and reports per-model/per-language stats. |

## Scripts

| File | Type | Change |
|---|---|---|
| [`scripts/run_pareto.py`](scripts/run_pareto.py) | **IMPL** | Was a 13-line placeholder; now a real three-way comparison (GPTCache vs. SCALM vs. Pareto) on the synthetic dataset with the mock embedder, threshold 0.60. |
| [`scripts/audit_rank_volatility.py`](scripts/audit_rank_volatility.py) | **IMPL + CITE** | Was a placeholder; now computes the Spearman rho between TSR rank and volatility using DBSCAN clustering + the volatility classifier on synthetic data. Also removed a leftover fabricated "Section IV method" citation from the docstring and CLI banner. |
| [`scripts/run_pareto_real.py`](scripts/run_pareto_real.py) | **NEW** | Real-data counterpart to `run_pareto.py`: three-way comparison (GPTCache vs. SCALM vs. Pareto) on real MOSS first-turn QA pairs with real SentenceTransformer (`all-MiniLM-L6-v2`) embeddings, threshold 0.90. Reports results as-is. |
| [`scripts/audit_rank_volatility_real.py`](scripts/audit_rank_volatility_real.py) | **NEW** | Real-data counterpart to `audit_rank_volatility.py`: Spearman rho between TSR rank and volatility on real MOSS data with real embeddings. |

## Real-data validation results (2026-09-07)

The three open acceptance-criteria items from `PARETO_DESIGN.md` §6
(items 1-3) were completed by running the new real-data scripts against
`data/moss-sample-10k.jsonl` (10,000 conversations, 56,236 turns, all
"Brainstorming" category):

**SCALM validation** (`scripts/run_scalm.py`, 5000 first-turn pairs,
capacity 100, warmup 100, threshold 0.90, real MiniLM embeddings):

```
Cache Hit Rate:       23.78%   (1,165 hits / 4,900 queries)
Token Saving Rate:    7.82%    (20,580 / 263,159 tokens)
LLM Calls Avoided:    3,735
```

This is the honest number — the validator exercises its real
clustering-driven rank admission (the frozen-after-warmup bug is fixed),
so 23.78% is a genuine measurement, not a frozen-warmup artifact.

**Three-way comparison** (`scripts/run_pareto_real.py`, 2000 first-turn
pairs, capacity 100, warmup 100, threshold 0.90):

```
System       |  Hit Ratio |  Token Saving Rate
----------------------------------------------
GPTCache     |      0.318 |              0.086
SCALM        |      0.185 |              0.068
Pareto       |      0.235 |              0.069
```

Reported as-is. Pareto beats SCALM on hit ratio on real data (0.235 vs
0.185) — the opposite of the synthetic run — while GPTCache still leads
on raw hit ratio (0.318) because it admits everything.

**Rank-volatility audit** (`scripts/audit_rank_volatility_real.py`,
2000 queries, DBSCAN eps=0.6):

```
Spearman rho (TSR rank vs. volatility): -0.354
Patterns analyzed: 5
```

Directionally supportive of the Pareto premise (negative rho), but
statistically weak — only 5 clusters formed, so the correlation is over
5 points. See `PARETO_AUDIT.md` §5c.

## Tests

| File | Type | Change |
|---|---|---|
| [`tests/pareto/test_cache.py`](tests/pareto/test_cache.py) | **NEW** | ParetoCache tests incl. regression tests for the classifier substring bug and the inverted reference-point bug. |
| [`tests/pareto/test_validator.py`](tests/pareto/test_validator.py) | **NEW** | ParetoValidator tests. |
| [`tests/pareto/test_hypervolume.py`](tests/pareto/test_hypervolume.py) | **NEW** | Hypervolume tests incl. reference-point validation. |
| [`tests/pareto/test_dominance_and_frontier.py`](tests/pareto/test_dominance_and_frontier.py) | **NEW** | Dominance + frontier tests. |
| [`tests/pareto/test_objectives.py`](tests/pareto/test_objectives.py) | **NEW** | Objective-vector tests. |
| [`tests/pareto/test_admission_and_threshold.py`](tests/pareto/test_admission_and_threshold.py) | **NEW → REMOVED** | JAS + threshold adapter tests. JAS tests removed with the dead code; threshold tests moved to `tests/pareto/test_threshold.py`. |
| [`tests/pareto/test_threshold.py`](tests/pareto/test_threshold.py) | **NEW** | Threshold adapter tests (moved from `test_admission_and_threshold.py` after JAS removal). |
| [`tests/test_classifiers.py`](tests/test_classifiers.py) | **NEW** | Classifier tests incl. regression for the single-letter-"i" substring bug. |
| [`tests/scalm/test_validator.py`](tests/scalm/test_validator.py) | **NEW** | Regression tests for the SCALM freeze-bug fix: verifies the cache admits entries after warmup and that patterns receive varied (non-LOW) ranks. |
| [`tests/test_vector_store.py`](tests/test_vector_store.py) | **NEW** | FAISSVectorStore regression tests for the silent-corruption bug: search-after-remove returns the correct entry, multiple removes, remove-then-add, remove-nonexistent, remove-all, get/all_entries consistency. |
| [`tests/test_lmsys_loader.py`](tests/test_lmsys_loader.py) | **NEW** | Regression tests for the LMSYS loader schema fix: loads the real OpenAI-chat schema, rejects the old guessed MOSS-style schema, skips malformed JSON/schema rows, respects `limit`, extracts first-turn/all-turn pairs from `role`/`content`, and reports model/language stats. |
| [`tests/test_moss_loader.py`](tests/test_moss_loader.py) | **NEW** | 17 synthetic-data tests for `MOSSLoader` (loading, limit, malformed lines, missing file, blank lines, text cleaning, first-turn/all-turns pairs, category filter, stats, len). **Caught a real bug**: `_clean_text()` leaked `<eom>`/`<eot>`/`<eoc>`/`<eor>` tokens into extracted answers. |
| [`tests/test_metrics.py`](tests/test_metrics.py) | **NEW** | 15 tests for `evaluation/metrics.py::compute_metrics` (hit ratio Eq. 3, token saving ratio Eq. 4, staleness rate, false hit rate, admission overhead, zero-division edge cases, `as_dict`). |
| [`tests/test_loader.py`](tests/test_loader.py) | **REF** | Converted from a manual script (no `test_` functions, not collected) into 3 real-data smoke tests guarded by `pytest.mark.skipif` (the `moss-sample-10k.jsonl` fixture is gitignored, so they skip in CI/fresh clones but run locally). |

## Bug Fix: MOSSLoader `<eom>` Token Leak

**Date**: 2026-03-25
**Severity**: Medium
**Found by**: New `test_moss_loader.py` tests (issue 8, zero test coverage)

`MOSSLoader._clean_text()` only stripped `<eoh>` tokens. The `<eom>` (end-of-message) tag — present in every MOSS answer — was never removed, leaking garbage into cached entries. Also added stripping for `<eot>`, `<eoc>`, and `<eor>` tags. Fixed in [`experiment/moss_loader.py`](experiment/moss_loader.py).

## Docs

| File | Type | Change |
|---|---|---|
| [`README.md`](../README.md) | **REF** | Updated to reflect two objectives (token savings + volatility), not four; fixed the repo-structure diagram; added a status table; fixed the mermaid diagram. |
| [`PARETO_AUDIT.md`](PARETO_AUDIT.md) | **NEW** | Full audit record: 8 citation fixes, 5 bugs, 1 limitation, test coverage, honest results, next steps. |
| [`README.md`](README.md) | **NEW** | Implementation-level backend doc (this file's sibling). |
| [`RUN.md`](RUN.md) | **NEW** | Commands to verify and run SCALM and Pareto separately. |
| [`CHANGES.md`](CHANGES.md) | **NEW** | This file. |

## Frontend (backend-aligned rewrite)

| File | Type | Change |
|---|---|---|
| [`frontend/src/cacheData.js`](../frontend/src/cacheData.js) | **REF** | Rewired from a 4-objective (token/latency/correctness/cost) maximizing-convention mock to the backend's real 2 objectives: `(-token_saving_proxy, volatility)` under the minimizing convention. `dominates()`/`computeParetoFrontier()`/`pruneByHypervolume()` now mirror `backend/pareto/dominance.py` and `backend/pareto/objectives.py`. Removed `jointAdmissionScore()` (JAS) — already removed from the backend (§4). Demo data remains illustrative but the *logic* is backend-aligned. |
| [`frontend/src/App.jsx`](../frontend/src/App.jsx) | **REF** | Removed JAS import/usage; candidate metrics now show token-saving proxy + volatility (not latency/correctness/cost); Pareto skyline chart plots volatility (x) vs token saving (y); footer and headers updated to "2D Objective Space (minimizing)". |

---

## Summary of impact

- **Test count: 19 → 144**, all passing locally (`python -m pytest backend/tests/ -q`). (115 − 6 JAS tests removed with the dead code; +17 MOSS loader, +15 metrics, +3 real-data smoke tests. The 3 `test_loader.py` smoke tests skip in CI because the gitignored `moss-sample-10k.jsonl` fixture is absent.)
- **9 fabricated citations fixed** across 9 files (the 8 original + a leftover "Section VI" in `evaluation/metrics.py` and a "Section IV method" in `scripts/audit_rank_volatility.py`).
- **9 real bugs fixed**, each with a regression test (incl. the SCALM frozen-after-warmup bug, the FAISS silent-corruption bug, the LMSYS wrong-schema bug, and the MOSS `<eom>` token-leak bug).
- **1 dead-code module removed**: `pareto/admission.py` (JAS) — never called by `ParetoCache`; cold-start admission is unconditional by design. JAS also removed from the frontend.
- **2 scripts implemented** (were placeholders).
- **3 docs created** (`backend/README.md`, `backend/RUN.md`, `backend/CHANGES.md`).
- **Frontend rewired to backend objectives**: 4-objective maximizing mock → 2-objective minimizing logic matching `backend/pareto/` (see "Frontend" section above).
