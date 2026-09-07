# RUN.md — How to Verify and Run SCALM and Pareto

This file documents the exact commands to (a) verify the test suite and
(b) run the SCALM baseline and the Pareto extension **separately**, so you
can reproduce results later. All commands run from the **project root**
(`d:\gowsi\miniproject\final_year_project`).

---

## 0. Prerequisites

```bash
# From the project root
cd backend
pip install -r requirements.txt
cd ..
```

Requirements: `scikit-learn`, `pytest`, `numpy`, `sentence-transformers`,
`tiktoken`, `pandas`, `faiss-cpu`.

> **Offline vs. real embeddings.** The mock embedder
> (`backend/embedding/mock_embedding.py`) is dependency-free and works
> with no network. The real embedder
> (`backend/embedding/sentence_transformer_provider.py`) downloads a model
> from Hugging Face on first use and needs network access. The offline
> commands below use the mock embedder so they run anywhere.

---

## 1. Verify the test suite

```bash
# Full suite (95 tests)
python -m pytest backend/tests/ -q

# Verbose, with per-test names
python -m pytest backend/tests/ -v

# Just the Pareto tests
python -m pytest backend/tests/pareto/ -q

# Just the classifier regression tests (substring-bug fix)
python -m pytest backend/tests/test_classifiers.py -q

# Just the GPTCache baseline tests
python -m pytest backend/tests/test_gptcache_baseline.py -q
```

Expected: **95 passed**.

---

## 2. Run the Pareto extension (offline, synthetic)

This is the three-way comparison: **GPTCache baseline vs. SCALM vs.
Pareto**, all on the synthetic dataset with the mock embedder. No network
needed.

```bash
python scripts/run_pareto.py
```

Output (sectioned): dataset summary, then per-system hit ratio and token
saving rate, then an interpretation block.

> **Reading the results.** The flat GPTCache baseline often wins on raw
> hit ratio here because it admits everything. Pareto is more conservative
> (rejects dominated candidates). SCALM's number is depressed by the
> frozen-after-warmup bug — see `backend/PARETO_AUDIT.md` §3 before
> interpreting it. These are **logic smoke tests**, not real-world
> benchmarks.

---

## 3. Run the rank-volatility audit (offline, synthetic)

This measures the Spearman correlation between a pattern's token-saving
rank and its volatility — the premise behind the Pareto extension.

```bash
python scripts/audit_rank_volatility.py
```

Output: number of clusters formed, the Spearman rho, and an interpretation
of whether the two objectives are in tension on this dataset.

---

## 4. Run SCALM separately (real dataset, needs network)

This runs the real `SCALMValidator` on the MOSS sample dataset with the
real embedding model. **Requires network access** to download the model and
to have `data/moss-sample-10k.jsonl` present.

```bash
python scripts/run_scalm.py
```

> If the sample file is missing, generate it first:
> `python scripts/extract_sample.py`

> **Known limitation.** `SCALMValidator` assigns every post-warmup entry
> `rank=LOW`, so once the cache fills during warmup it never admits
> anything new. The reported hit rate reflects how often later queries
> match the frozen warmup set, **not** SCALM's real clustering/ranking
> mechanism. See `backend/PARETO_AUDIT.md` §3.

---

## 5. Run SCALM separately (offline, mock embedder)

To run SCALM without network access, inject the mock embedder. There is no
dedicated script for this, but you can run it inline:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.experiment.synthetic_dataset import generate_dataset
from backend.scalm.validator import SCALMValidator

qa = [(p.query_text, p.answer_text) for p in generate_dataset(300, reuse_rate=0.15, seed=42)]
v = SCALMValidator(capacity=20, similarity_threshold=0.60, embedding_provider=MockEmbeddingProvider())
print(v.run(qa, warmup_count=100))
"
```

---

## 6. Run Pareto separately (offline, mock embedder)

The Pareto validator defaults to the mock embedder, so it runs offline with
no extra setup:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from backend.experiment.synthetic_dataset import generate_dataset
from backend.pareto.validator import ParetoValidator

qa = [(p.query_text, p.answer_text) for p in generate_dataset(300, reuse_rate=0.15, seed=42)]
v = ParetoValidator(capacity=20, similarity_threshold=0.60)
print(v.run(qa, warmup_count=100))
"
```

---

## 7. Run Pareto separately (real dataset, needs network)

To run the Pareto validator on the real MOSS data with real embeddings,
inject the real embedding provider:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from backend.embedding.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from backend.experiment.moss_loader import MOSSLoader
from backend.pareto.validator import ParetoValidator

loader = MOSSLoader('data/moss-sample-10k.jsonl')
qa = loader.get_first_turn_pairs()[:5000]
v = ParetoValidator(capacity=100, embedding_provider=SentenceTransformerEmbeddingProvider())
print(v.run(qa, warmup_count=100))
"
```

> **Threshold note.** The real embedder produces 0.90+ similarity for
> genuine paraphrases, so the default 0.90 threshold is appropriate here.
> The synthetic runs use 0.60 because the mock embedder is lexical-overlap
> based and can't reach 0.90 for paraphrases.

---

## Quick reference table

| Task | Command | Network? |
|---|---|---|
| Verify tests | `python -m pytest backend/tests/ -q` | No |
| Pareto 3-way comparison | `python scripts/run_pareto.py` | No |
| Rank-volatility audit | `python scripts/audit_rank_volatility.py` | No |
| SCALM (real data) | `python scripts/run_scalm.py` | **Yes** |
| SCALM (offline) | inline snippet (§5) | No |
| Pareto (offline) | inline snippet (§6) | No |
| Pareto (real data) | inline snippet (§7) | **Yes** |

---

## Interpreting results honestly

- These are **logic smoke tests** on synthetic data, not real-world
  benchmarks. The mock embedder only captures lexical overlap.
- The flat GPTCache baseline often beats Pareto on raw hit ratio because
  it admits everything; Pareto trades raw hit ratio for lower false-hit
  risk, which isn't modeled yet.
- SCALM's numbers are depressed by the frozen-after-warmup bug
  (`PARETO_AUDIT.md` §3) and should not be trusted until that's fixed.
- The real test of the Pareto premise is running
  `scripts/audit_rank_volatility.py` on **real data** with real embeddings
  (`PARETO_AUDIT.md` §7, step 2).
