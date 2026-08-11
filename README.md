# Pareto-Optimized Multi-Objective Semantic Cache Management for Large Language Models

A semantic caching system for LLM chat services, built on top of [SCALM](https://arxiv.org/abs/2406.00025) (Semantic Caching for Automated Chat Services with Large Language Models). This project extends SCALM's single-score, rank-based cache admission and eviction with **Pareto Skyline multi-objective optimization** — jointly considering token savings, response latency, answer correctness, and computation cost instead of a single heuristic rank.

---

## Overview

LLM chat services incur significant latency and inference cost per query. Semantic caching addresses this by reusing cached responses for semantically similar queries instead of recomputing them.

Most existing semantic caches, including SCALM, make cache decisions using a **single heuristic score** (usually token savings), ignoring other factors that matter in production — latency, correctness, and compute cost. This project treats cache admission and eviction as a genuine **multi-objective problem**, retaining only cache entries that represent the best trade-offs across all objectives at once.

## Proposed System

1. **Semantic clustering** — user queries are embedded and grouped using hierarchical semantic clustering (SCALM's CO-HSC/SE-HSC approach).
2. **Semantic cache lookup** — a query is checked against the cache via similarity search; a hit returns the cached response directly, a miss is forwarded to the LLM.
3. **Multi-objective evaluation** — every candidate cache entry is scored across multiple objectives simultaneously: token savings, response latency, answer correctness, and computation cost.
4. **Pareto Skyline Selection** — instead of a single weighted score, the system retains only **non-dominated (Pareto-optimal) cache entries**.
5. **Adaptive cache admission/eviction** — decisions adjust as the workload and cache state change.

## Architecture

```mermaid
flowchart TD
    A[User Query] --> B[Query Embedding]

    subgraph SCL[Semantic Cache Layer]
        B --> C[Semantic Similarity Search]
        C -->|Hit| D[Return Cached Response]
        C -->|Miss| E[LLM Inference]
        E --> F[Generated Response]
        F --> G["Candidate Cache Entry (vector_key, answer_text)"]
    end

    G --> H["Multi-Objective Evaluation:
    1. Token Saving
    2. Response Latency
    3. Answer Correctness
    4. Computation Cost"]
    H --> I["Pareto Skyline Selection
    (find the best trade-offs)"]
    I --> J[Select Non-Dominated Cache Entries]
    J --> K[Cache Admission / Eviction]
    K --> L[Updated Semantic Cache]
    L -.-> C
```

## Repository Structure

```
├── backend
│   ├── clustering
│   │   ├── __init__.py
│   │   └── dbscan_clustering.py
│   ├── domain
│   │   ├── __init__.py
│   │   └── entities.py
│   ├── embedding
│   │   ├── __init__.py
│   │   ├── mock_embedding.py
│   │   └── token_counter.py
│   ├── interfaces
│   │   ├── __init__.py
│   │   └── protocols.py
│   ├── tests
│   │   ├── __init__.py
│   │   ├── test_admission_eviction.py
│   │   ├── test_clustering.py
│   │   ├── test_e2e_cache.py
│   │   └── test_vector_store.py
│   ├── vector_store
│   │   ├── __init__.py
│   │   └── in_memory.py
│   ├── __init__.py
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── App.jsx
│   │   ├── cacheData.js
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── README.md
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── vercel.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

- **`backend/`** — the semantic cache engine itself: embedding, clustering, admission, eviction, and lookup logic. See [`backend/README.md`](backend/README.md) for implementation-level details.
- **`frontend/`** — a lightweight demo UI that visualizes how a query flows through the cache (embedding → similarity search → HIT/MISS → cache update). Live demo: [pareto-semantic-cache-demo](https://pareto-semantic-cache-demo-three.vercel.app/)

## Getting Started

### Backend

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Frontend (demo)

```bash
cd frontend
npm install
npm run dev
```
