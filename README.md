# Pareto-Based Semantic Cache Demo

A frontend-only React visualization for demonstrating the proposed semantic caching workflow.

## What this demo represents

### SCALM-inspired portion
- Query embedding
- Semantic similarity search
- Cache hit/miss decision
- LLM inference on cache miss

### Proposed portion
- Candidate cache entry
- Multi-objective evaluation
- Pareto skyline / non-dominated selection
- Cache admission / eviction
- Updated semantic cache

## Run

```bash
npm install
npm run dev
```

Then open the local Vite URL shown in the terminal.

## Demo queries

- `Explain machine learning in simple words` → semantic cache hit
- `What are neural networks?` → semantic cache hit
- `Tell me about quantum computing` → cache miss → LLM → candidate → Pareto flow

## Important

This is a visualization/prototype for the presentation. It does not call a real LLM or embedding model and does not claim real backend performance.
