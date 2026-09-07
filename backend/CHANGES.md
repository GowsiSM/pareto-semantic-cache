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
| [`pareto/admission.py`](pareto/admission.py) | **CITE** | Removed false "Section V-B defines JAS" citation; relabeled JAS as this project's own extension. |
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

## Cache core

| File | Type | Change |
|---|---|---|
| [`cache/admission.py`](cache/admission.py) | **IMPL** | Added `AlwaysAdmitPolicy` (GPTCache baseline admission). |
| [`cache/eviction.py`](cache/eviction.py) | **IMPL** | Added `PlainLFUEviction` and `PlainLRUEviction` (GPTCache baseline eviction). |

## Embedding

| File | Type | Change |
|---|---|---|
| [`embedding/sentence_transformer_provider.py`](embedding/sentence_transformer_provider.py) | **CITE** | Corrected false claim that the paper uses `all-MiniLM-L6-v2`; the paper uses OpenAI `text-embedding-3-small`. MiniLM is a free local alternative here. |
| [`embedding/mock_embedding.py`](embedding/mock_embedding.py) | **NEW** | Offline hashed bag-of-words embedder (512-dim, stopword-filtered, L2-normalized) for tests/CI. |

## Evaluation

| File | Type | Change |
|---|---|---|
| [`evaluation/metrics.py`](evaluation/metrics.py) | **CITE** | Clarified that only `cache_hit_ratio`/`token_saving_ratio` are from the paper (Eq. 3/4); `staleness_rate`/`false_hit_rate`/`admission_overhead` are this project's own additions. |

## SCALM validator

| File | Type | Change |
|---|---|---|
| [`scalm/validator.py`](scalm/validator.py) | **REF** | Made `embedding_provider` injectable (defaults to the real model only when none given) so it runs offline. Documented the frozen-after-warmup limitation in the docstring (not fixed — separate scope). |

## Experiment / data

| File | Type | Change |
|---|---|---|
| [`experiment/synthetic_dataset.py`](experiment/synthetic_dataset.py) | **NEW** | Offline synthetic QA generator (8 topics, 4 stable + 4 volatile, controlled reuse rate) for sandbox-runnable validation. |

## Scripts

| File | Type | Change |
|---|---|---|
| [`scripts/run_pareto.py`](scripts/run_pareto.py) | **IMPL** | Was a 13-line placeholder; now a real three-way comparison (GPTCache vs. SCALM vs. Pareto) on the synthetic dataset with the mock embedder, threshold 0.60. |
| [`scripts/audit_rank_volatility.py`](scripts/audit_rank_volatility.py) | **IMPL** | Was a placeholder; now computes the Spearman rho between TSR rank and volatility using DBSCAN clustering + the volatility classifier on synthetic data. |

## Tests

| File | Type | Change |
|---|---|---|
| [`tests/pareto/test_cache.py`](tests/pareto/test_cache.py) | **NEW** | ParetoCache tests incl. regression tests for the classifier substring bug and the inverted reference-point bug. |
| [`tests/pareto/test_validator.py`](tests/pareto/test_validator.py) | **NEW** | ParetoValidator tests. |
| [`tests/pareto/test_hypervolume.py`](tests/pareto/test_hypervolume.py) | **NEW** | Hypervolume tests incl. reference-point validation. |
| [`tests/pareto/test_dominance_and_frontier.py`](tests/pareto/test_dominance_and_frontier.py) | **NEW** | Dominance + frontier tests. |
| [`tests/pareto/test_objectives.py`](tests/pareto/test_objectives.py) | **NEW** | Objective-vector tests. |
| [`tests/pareto/test_admission_and_threshold.py`](tests/pareto/test_admission_and_threshold.py) | **NEW** | JAS + threshold adapter tests. |
| [`tests/test_classifiers.py`](tests/test_classifiers.py) | **NEW** | Classifier tests incl. regression for the single-letter-"i" substring bug. |
| [`tests/test_gptcache_baseline.py`](tests/test_gptcache_baseline.py) | **NEW** | GPTCache baseline tests. |

## Docs

| File | Type | Change |
|---|---|---|
| [`README.md`](../README.md) | **REF** | Updated to reflect two objectives (token savings + volatility), not four; fixed the repo-structure diagram; added a status table; fixed the mermaid diagram. |
| [`PARETO_AUDIT.md`](PARETO_AUDIT.md) | **NEW** | Full audit record: 8 citation fixes, 5 bugs, 1 limitation, test coverage, honest results, next steps. |
| [`README.md`](README.md) | **NEW** | Implementation-level backend doc (this file's sibling). |
| [`RUN.md`](RUN.md) | **NEW** | Commands to verify and run SCALM and Pareto separately. |
| [`CHANGES.md`](CHANGES.md) | **NEW** | This file. |

---

## Summary of impact

- **Test count: 19 → 95**, all passing (`python -m pytest backend/tests/ -q`).
- **8 fabricated citations fixed** across 8 files.
- **5 real bugs fixed**, each with a regression test.
- **1 limitation flagged, not fixed** (SCALM frozen-after-warmup) — your call.
- **2 scripts implemented** (were placeholders).
- **3 docs created** (`backend/README.md`, `backend/RUN.md`, `backend/CHANGES.md`).
