# SemantiCache Frontend

A standalone React + TypeScript + Vite frontend for comparing GPTCache,
SCALM, and Pareto semantic cache admission strategies. This frontend
contains **no cache algorithm logic** -- every number shown comes from a
real HTTP request to your backend.

The repository now includes a thin FastAPI wrapper around the existing
validators at `backend/api.py`. Nothing in the frontend fabricates or falls
back to fake data -- if the API isn't running, the UI shows a real connection
error.

## Setup

```bash
npm install
cp .env.example .env
```

PowerShell equivalent for the environment file:

```powershell
Copy-Item .env.example .env
```

In a second terminal, from the project root:

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

Then, from `frontend/`, run the development UI:

```bash
npm run dev
```

PowerShell commands from the repository root:

```powershell
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
Set-Location frontend
npm run dev
```

```bash
npm run build   # type-checks with tsc, then builds with Vite
npm run test    # runs the vitest suite
npm run preview # serve the production build locally
```

## Backend API Contract

The backend implements two endpoints:

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

The handler loads the selected dataset, creates the selected embedding
provider, and runs all three existing validators against the same QA pairs.
Synthetic/mock runs are fully offline; MOSS/sentence-transformer runs require
the dataset and model dependencies.

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
