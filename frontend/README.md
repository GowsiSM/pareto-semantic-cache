# SemantiCache Frontend

A React + TypeScript + Vite frontend for comparing GPTCache, SCALM, and the
SPARC/Pareto semantic-cache extension. Cache decisions and reported metrics
come from the FastAPI backend; the frontend renders the returned trace and
experiment data.

The repository includes a thin FastAPI backend at `backend/api.py`. Its CORS
configuration allows local frontend development origins such as
`http://localhost:3000` and `http://localhost:5173`.
Nothing here fabricates or falls back to fake data -- if the API is not
running, the UI shows a real connection error.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Run the backend from the repository root in a second terminal:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

Then run the frontend commands from `frontend/`. On PowerShell, use
`Copy-Item .env.example .env` instead of `cp .env.example .env`.

```bash
npm run build   # type-checks with tsc, then builds with Vite
npm run test    # runs the vitest suite
npm run preview # serve the production build locally
```

## Backend API

The FastAPI backend exposes these endpoints:

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

### `POST /api/experiments/trace`

Accepts the same request fields as `/api/experiments/run`, plus:

```json
{
  "trace_index": 0
}
```

`trace_index` is zero-based within the replay phase (after `warmup_count`).
Optional `query_text` and `answer_text` fields let the presenter override the
selected workload query; both must be supplied together.
The response contains the selected query, similarity and effective threshold
for SCALM and SPARC, the nearest cached query, admission result, evicted
entries, cache snapshots, and SPARC objective/frontier values. A miss uses
that dataset row's recorded response as the candidate by default; with an
override, it uses the supplied response. No LLM call is made.
Volatility is the project's keyword-classifier score, not ground-truth answer
freshness. Per-query latency is not currently exposed.
The current Pareto eviction implementation also applies its contribution
calculation to dominated entries when such entries exist; that tie-break
needs independent algorithm validation and is labeled as an implementation
limitation in the trace view.

The trace replays the selected workload through the existing cache classes.
The aggregate experiment endpoint continues to run GPTCache, SCALM, and
Pareto on the same workload.

CORS: since this frontend runs on a different origin/port than the
backend during development, make sure your API sends
`Access-Control-Allow-Origin` headers (FastAPI's `CORSMiddleware`, or
Flask-CORS).

## Project structure

```
src/
|-- App.tsx                         # active research console and demo flow
|-- conference.css                  # scoped conference visual system
|-- api/
|   |-- types.ts                    # experiment and trace response types
|   `-- client.ts                   # HTTP wrappers with explicit API errors
|-- hooks/
|   |-- useExperiment.ts            # experiment request state
|   `-- useDecisionTrace.ts         # workload replay request state
|-- components/
|   |-- DecisionJourney.tsx        # backend trace, decisions, cache snapshots
|   |-- ParetoTradeoffPlot.tsx     # accessible plot of actual objective values
|   |-- RunExperimentPanel.tsx     # measured-run and trace controls
|   |-- ResultsTable.tsx
|   |-- ResultsCharts.tsx
|   `-- ConclusionSection.tsx     # computed from measured results
`-- test/
    |-- ConclusionSection.test.tsx
    `-- DecisionJourney.test.tsx
```

## Presentation mode and data limits

Presentation mode hides utility controls and keeps the selected query and
decision summary visible. Guided stages jump to real views; they do not
simulate streaming or insert artificial delays. Reset clears loaded results
and restores the replay controls to their defaults.

The measured-results view focuses on the SCALM–SPARC head-to-head. GPTCache
is still run by the backend and is available through the “Show GPTCache
reference baseline” checkbox; the UI labels it as a separate reference
because its unconditional-admission policy differs from the staged comparison.
The decision-trace control defaults to replay event 25 (after warmup) so the
cache is likely to be full, but the returned before-event occupancy indicates
whether it actually was.

The current backend does not expose per-query latency or ground-truth answer
freshness. Aggregate staleness values follow the validators' classifier-based
definition. Synthetic embeddings are lexical test embeddings and should not
be presented as real semantic-model experimental evidence; use MOSS with the
configured SentenceTransformer when reporting real-data results.

The trace distinguishes admission from Pareto-frontier membership: an
under-capacity cache admits candidates unconditionally, even if a candidate is
dominated. A rejected candidate does not evict an entry.
