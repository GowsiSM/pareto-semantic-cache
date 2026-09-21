# SemantiCache Frontend

A standalone React + TypeScript + Vite frontend for comparing GPTCache,
SCALM, and Pareto semantic cache admission strategies. This frontend
contains **no cache algorithm logic** -- every number shown comes from a
real HTTP request to your backend.

## Important: the backend API this frontend expects does not exist yet

The Python project this frontend was built for (`pareto-semantic-cache`)
currently exposes its validators as **CLI scripts** (`run_pareto.py`,
`run_scalm.py`, `audit_rank_volatility.py`, etc.) -- there is no HTTP
server anywhere in it yet. This frontend calls a REST API that you need
to add to that backend (e.g. a thin FastAPI or Flask wrapper around the
existing `ParetoValidator` / `SCALMValidator` / `GPTCache` classes).
Nothing here fabricates or falls back to fake data -- if the API isn't
running, the UI will show a real connection error, not placeholder
numbers.

## Setup

```bash
npm install
cp .env.example .env
# edit .env if your backend runs somewhere other than http://localhost:8000
npm run dev
```

```bash
npm run build   # type-checks with tsc, then builds with Vite
npm run test    # runs the vitest suite
npm run preview # serve the production build locally
```

## Backend API Contract

Your backend needs to implement two endpoints:

### `GET /api/health`

Returns `200 OK` with any body. Used only for a lightweight connectivity
check.

### `POST /api/experiments/run`

**Request body:**

```json
{
  "dataset": "synthetic",
  "n_queries": 300,
  "capacity": 20,
  "similarity_threshold": 0.6,
  "warmup_count": 100,
  "embedding": "mock",
  "seed": 42
}
```

- `dataset`: `"synthetic"` (uses `backend/experiment/synthetic_dataset.py`,
  no network needed) or `"moss"` (uses `backend/experiment/moss_loader.py`
  against your real MOSS sample file, requires the real embedding model).
- `embedding`: `"mock"` or `"sentence-transformer"`.

**Response body** (field names match your existing validators'
`.run()` return dicts almost exactly -- this is deliberate, so wiring
this up should mostly be translation, not new logic):

```json
{
  "request": { "...": "echo of the request" },
  "systems": {
    "gptcache": {
      "hit_rate": 0.318,
      "token_saving_rate": 0.086,
      "staleness_rate": 0.008,
      "false_hit_rate": 0.0,
      "hits": 605,
      "misses": 1295,
      "total_queries": 1900
    },
    "scalm": { "...": "same shape" },
    "pareto": { "...": "same shape" }
  },
  "meta": {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "duration_ms": 4213,
    "dataset_size": 2000
  }
}
```

On error, return a non-2xx status with:

```json
{ "error": "short message", "detail": "optional longer detail" }
```

**Sketch of what the backend handler needs to do** (pseudocode, not
provided -- you asked for frontend only):

```python
# 1. Build the dataset (synthetic_dataset.generate_dataset(...) or
#    MOSSLoader(...).get_first_turn_pairs())
# 2. Build the embedding provider (MockEmbeddingProvider or
#    SentenceTransformerEmbeddingProvider)
# 3. Run all three: GPTCache, SCALMValidator, ParetoValidator, with the
#    SAME dataset, capacity, threshold, and embedding provider instance
# 4. Return their .run() results, renamed into the "systems" shape above
```

CORS: since this frontend runs on a different origin/port than the
backend during development, make sure your API sends
`Access-Control-Allow-Origin` headers (FastAPI's `CORSMiddleware`, or
Flask-CORS).

## Project structure

```
src/
|-- api/
|   |-- types.ts        # Request/response types matching the contract above
|   `-- client.ts        # fetch wrapper -- throws real errors, never fakes data
|-- hooks/
|   `-- useExperiment.ts # idle/loading/success/error state for a run
|-- components/
|   |-- Hero.tsx
|   |-- ArchitectureDiagram.tsx   # static SVG-style illustration only
|   |-- HowParetoWorks.tsx         # static illustration only
|   |-- RunExperimentPanel.tsx     # form -> calls the real API
|   |-- StatusBanner.tsx
|   |-- ResultsTable.tsx
|   |-- ResultsCharts.tsx          # recharts, driven entirely by API data
|   `-- ConclusionSection.tsx      # computed from results every render,
|                                    never a fixed "Pareto wins" narrative
`-- test/
    `-- ConclusionSection.test.tsx # verifies the conclusion logic is
                                     genuinely data-driven, not hardcoded
```

## Design

Minimal black-and-white, monospace accents, thin 1px borders, no rounded
corners -- developer-tool aesthetic rather than a marketing-site look.
