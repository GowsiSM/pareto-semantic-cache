"""HTTP API for running the frontend's three-way cache experiment."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from backend.baselines.gptcache import GPTCache
from backend.classifier.domain_classifier import DomainClassifier
from backend.classifier.volatility_classifier import VolatilityClassifier
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.embedding.token_counter import SimpleTokenCounter
from backend.experiment.moss_loader import MOSSLoader
from backend.experiment.synthetic_dataset import generate_dataset
from backend.pareto.validator import ParetoValidator
from backend.pareto.dominance import dominates, pareto_frontier
from backend.pareto.objectives import objective_vector
from backend.scalm.validator import SCALMValidator
from backend.domain.entities import CacheEntry, PatternRank, SemanticPattern
from backend.interfaces.protocols import EmbeddingProvider
from backend.vector_store.in_memory import InMemoryVectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOSS_DATASET_CANDIDATES = (
    PROJECT_ROOT / "data" / "moss-sample-10k.jsonl",
    PROJECT_ROOT / "moss-sample-10k.jsonl",
)


class ExperimentRequest(BaseModel):
    dataset: Literal["synthetic", "moss"] = "synthetic"
    n_queries: int = Field(default=300, ge=1, le=20_000)
    capacity: int = Field(default=20, ge=1, le=2_000)
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    warmup_count: int = Field(default=100, ge=0)
    embedding: Literal["mock", "sentence-transformer"] = "mock"
    seed: int = 42

    @model_validator(mode="after")
    def validate_warmup(self) -> "ExperimentRequest":
        if self.warmup_count > self.n_queries:
            raise ValueError("warmup_count cannot exceed n_queries")
        if self.dataset == "moss" and self.embedding != "sentence-transformer":
            raise ValueError("MOSS experiments require sentence-transformer embeddings")
        return self


class TraceRequest(ExperimentRequest):
    trace_index: int = Field(default=0, ge=0)
    query_text: str | None = Field(default=None, min_length=1, max_length=4_000)
    answer_text: str | None = Field(default=None, min_length=1, max_length=20_000)

    @model_validator(mode="after")
    def validate_trace_index(self) -> "TraceRequest":
        replay_count = self.n_queries - self.warmup_count
        if self.trace_index >= replay_count:
            raise ValueError("trace_index must identify a query after the warmup phase")
        if (self.query_text is None) != (self.answer_text is None):
            raise ValueError("query_text and answer_text must be provided together")
        if self.query_text is not None and not self.query_text.strip():
            raise ValueError("query_text cannot be blank")
        if self.answer_text is not None and not self.answer_text.strip():
            raise ValueError("answer_text cannot be blank")
        return self


app = FastAPI(title="SemantiCache API")
app.add_middleware(
    CORSMiddleware,
    # Allow local Vite/React dev servers regardless of whether they use
    # port 3000, 5173, or another local development port.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    messages = "; ".join(error["msg"] for error in exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid experiment request", "detail": messages},
    )


def _load_pairs(request: ExperimentRequest) -> list[tuple[str, str]]:
    if request.dataset == "synthetic":
        return [
            (pair.query_text, pair.answer_text)
            for pair in generate_dataset(request.n_queries, seed=request.seed)
        ]

    dataset_path = next(
        (path for path in MOSS_DATASET_CANDIDATES if path.exists()), None
    )
    if dataset_path is None:
        checked = ", ".join(str(path) for path in MOSS_DATASET_CANDIDATES)
        raise HTTPException(
            status_code=404,
            detail=f"MOSS dataset not found. Checked: {checked}",
        )

    pairs = MOSSLoader(str(dataset_path)).get_first_turn_pairs()
    pairs = pairs[: request.n_queries]
    if not pairs:
        raise HTTPException(status_code=422, detail="MOSS dataset contains no usable QA pairs")
    return pairs


def _build_embedding(request: ExperimentRequest) -> EmbeddingProvider:
    if request.embedding == "mock":
        return MockEmbeddingProvider()

    from backend.embedding.sentence_transformer_provider import (
        SentenceTransformerEmbeddingProvider,
    )

    return SentenceTransformerEmbeddingProvider()


def _run_gptcache(
    qa_pairs: list[tuple[str, str]],
    capacity: int,
    threshold: float,
    warmup_count: int,
    embedding_provider: EmbeddingProvider,
) -> dict:
    cache = GPTCache(
        embedding_provider=embedding_provider,
        vector_store=InMemoryVectorStore(),
        token_counter=SimpleTokenCounter(),
        capacity=capacity,
        similarity_threshold=threshold,
        eviction="lfu",
    )
    token_counter = SimpleTokenCounter()
    stats = {"hits": 0, "misses": 0, "tokens_saved": 0, "total_tokens": 0}

    for query, response in qa_pairs[:warmup_count]:
        cache.store(query, response)
    for query, response in qa_pairs[warmup_count:]:
        response_tokens = token_counter.count(response)
        stats["total_tokens"] += response_tokens
        result = cache.lookup(query)
        if result.hit:
            stats["hits"] += 1
            stats["tokens_saved"] += response_tokens
        else:
            stats["misses"] += 1
            cache.store(query, response)

    total = stats["hits"] + stats["misses"]
    return {
        "hit_rate": stats["hits"] / total if total else 0,
        "token_saving_rate": (
            stats["tokens_saved"] / stats["total_tokens"]
            if stats["total_tokens"]
            else 0
        ),
        "staleness_rate": 0,
        "false_hit_rate": 0,
        "hits": stats["hits"],
        "misses": stats["misses"],
        "total_queries": total,
    }


def _run_experiment(request: ExperimentRequest) -> dict:
    started = time.perf_counter()
    qa_pairs = _load_pairs(request)
    if request.warmup_count > len(qa_pairs):
        raise HTTPException(
            status_code=422,
            detail=f"warmup_count cannot exceed available dataset size ({len(qa_pairs)})",
        )

    embedding_provider = _build_embedding(request)
    systems = {
        "gptcache": _run_gptcache(
            qa_pairs,
            request.capacity,
            request.similarity_threshold,
            request.warmup_count,
            embedding_provider,
        ),
        "scalm": SCALMValidator(
            capacity=request.capacity,
            similarity_threshold=request.similarity_threshold,
            embedding_provider=embedding_provider,
        ).run(qa_pairs, warmup_count=request.warmup_count),
        "pareto": ParetoValidator(
            capacity=request.capacity,
            similarity_threshold=request.similarity_threshold,
            embedding_provider=embedding_provider,
        ).run(qa_pairs, warmup_count=request.warmup_count),
    }
    return {
        "request": request.model_dump(),
        "systems": systems,
        "meta": {
            "embedding_model": (
                "mock-hashed-bag-of-words"
                if request.embedding == "mock"
                else "sentence-transformers/all-MiniLM-L6-v2"
            ),
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "dataset_size": len(qa_pairs),
        },
    }


def _entry_trace(entry: CacheEntry, volatility_classifier: VolatilityClassifier) -> dict:
    volatility = volatility_classifier.volatility_score(entry.query_text)
    saving_proxy = entry.total_token_count
    return {
        "id": entry.entry_id,
        "query": entry.query_text,
        "token_saving_proxy": saving_proxy,
        "volatility": volatility,
        "objective": [-float(saving_proxy), volatility],
        "hits": entry.hit_count,
    }


def _cache_snapshot(cache, volatility_classifier: VolatilityClassifier) -> list[dict]:
    return [_entry_trace(entry, volatility_classifier) for entry in cache.entries]


def _replay_trace(request: TraceRequest) -> dict:
    qa_pairs = _load_pairs(request)
    if request.warmup_count > len(qa_pairs):
        raise HTTPException(
            status_code=422,
            detail=f"warmup_count cannot exceed available dataset size ({len(qa_pairs)})",
        )
    if request.trace_index >= len(qa_pairs) - request.warmup_count:
        raise HTTPException(
            status_code=422,
            detail="trace_index exceeds the available replay queries in this dataset",
        )

    target_index = request.warmup_count + request.trace_index
    query, answer = qa_pairs[target_index]
    answer_source = "selected dataset response; no LLM call is made"
    if request.query_text is not None and request.answer_text is not None:
        query, answer = request.query_text, request.answer_text
        answer_source = "user-provided candidate response; no LLM call is made"
        query_source = "user input"
    else:
        query_source = "selected dataset event"
    embedding_provider = _build_embedding(request)
    scalm = SCALMValidator(
        capacity=request.capacity,
        similarity_threshold=request.similarity_threshold,
        embedding_provider=embedding_provider,
    )
    pareto = ParetoValidator(
        capacity=request.capacity,
        similarity_threshold=request.similarity_threshold,
        embedding_provider=embedding_provider,
    )

    for index, (warm_query, warm_answer) in enumerate(qa_pairs[:request.warmup_count]):
        pattern = SemanticPattern(
            pattern_id=f"warm_{index}",
            round_index=1,
            centroid=[0.0] * 384,
            rank=PatternRank.LOW,
        )
        scalm.cache.store(warm_query, warm_answer, pattern)
        pareto.cache.store(warm_query, warm_answer)

    for replay_query, replay_answer in qa_pairs[request.warmup_count:target_index]:
        scalm_result = scalm.cache.lookup(replay_query)
        if not scalm_result.hit:
            scalm.stats["llm_calls"] += 1
            query_embedding = embedding_provider.embed(replay_query)
            pattern = scalm._compute_pattern_for_query(query_embedding)
            pattern.pattern_id = f"miss_{scalm.stats['llm_calls']}"
            scalm.cache.store(replay_query, replay_answer, pattern)

        pareto_result = pareto.cache.lookup(replay_query)
        if not pareto_result.hit:
            pareto.stats["llm_calls"] += 1
            pareto.cache.store(replay_query, replay_answer)

    volatility_classifier = VolatilityClassifier()
    domain_classifier = DomainClassifier()

    def evicted_entries(before: list[CacheEntry], after_ids: set[str]) -> list[str]:
        return [entry.query_text for entry in before if entry.entry_id not in after_ids]

    scalm_before = scalm.cache.entries
    scalm_cache_was_full = len(scalm_before) >= request.capacity
    scalm_lookup = scalm.cache.lookup(query)
    scalm_pattern = None
    scalm_admitted = None
    if not scalm_lookup.hit:
        scalm.stats["llm_calls"] += 1
        pattern = scalm._compute_pattern_for_query(embedding_provider.embed(query))
        pattern.pattern_id = f"miss_{scalm.stats['llm_calls']}"
        scalm_pattern = pattern.rank.value
        scalm_admitted = scalm.cache.store(query, answer, pattern) is not None
    scalm_after = scalm.cache.entries
    scalm_after_ids = {entry.entry_id for entry in scalm_after}
    scalm_evicted = evicted_entries(scalm_before, scalm_after_ids)

    pareto_before = pareto.cache.entries
    pareto_lookup = pareto.cache.lookup(query)
    candidate_volatility = volatility_classifier.volatility_score(query)
    candidate_point = None
    candidate_frontier = None
    dominators = []
    pareto_admitted = None
    pareto_candidate_entry_id = None
    pareto_had_dominated_entries = False
    pareto_cache_was_full = len(pareto_before) >= request.capacity
    if not pareto_lookup.hit:
        candidate_tokens = pareto.token_counter.count(query) + pareto.token_counter.count(answer)
        candidate = CacheEntry(
            entry_id="trace_candidate",
            query_text=query,
            answer_text=answer,
            embedding=embedding_provider.embed(query),
            pattern_id=None,
            query_token_count=pareto.token_counter.count(query),
            answer_token_count=pareto.token_counter.count(answer),
        )
        candidate_objective = objective_vector(candidate, candidate_volatility)
        existing_objectives = [
            objective_vector(
                entry,
                volatility_classifier.volatility_score(entry.query_text),
            )
            for entry in pareto_before
        ]
        combined_objectives = existing_objectives + [candidate_objective]
        frontier_values = pareto_frontier(combined_objectives)
        candidate_frontier = candidate_objective in frontier_values
        pareto_had_dominated_entries = any(
            objective not in frontier_values for objective in existing_objectives
        )
        dominators = [
            pareto_before[index].entry_id
            for index, objective in enumerate(existing_objectives)
            if dominates(objective, candidate_objective)
        ]
        candidate_point = {
            "id": "trace_candidate",
            "query": query,
            "token_saving_proxy": candidate_tokens,
            "volatility": candidate_volatility,
            "objective": list(candidate_objective),
            "is_candidate": True,
            "is_frontier": candidate_frontier,
        }
        combined_point_details = [
            _entry_trace(entry, volatility_classifier) for entry in pareto_before
        ] + [candidate_point]
        points = [
            {
                **point,
                "is_candidate": False,
                "is_frontier": combined_objectives[point_index] in frontier_values,
                "dominated_by": [
                    other["id"]
                    for other_index, (other, other_objective) in enumerate(
                        zip(combined_point_details, combined_objectives)
                    )
                    if other_index != point_index
                    and dominates(other_objective, combined_objectives[point_index])
                ],
            }
            for point_index, point in enumerate(combined_point_details[:-1])
        ]
        points.append({
            **candidate_point,
            "dominated_by": dominators,
        })
    else:
        existing_objectives = [
            objective_vector(
                entry,
                volatility_classifier.volatility_score(entry.query_text),
            )
            for entry in pareto_before
        ]
        frontier_values = pareto_frontier(existing_objectives)
        points = [
            {
                **_entry_trace(entry, volatility_classifier),
                "is_candidate": False,
                "is_frontier": objective in frontier_values,
                "dominated_by": [
                    other.entry_id
                    for other_index, (other, other_objective) in enumerate(
                        zip(pareto_before, existing_objectives)
                    )
                    if other_index != point_index
                    and dominates(other_objective, existing_objectives[point_index])
                ],
            }
            for point_index, (entry, objective) in enumerate(zip(pareto_before, existing_objectives))
        ]

    if not pareto_lookup.hit:
        pareto.stats["llm_calls"] += 1
        stored_candidate = pareto.cache.store(query, answer)
        pareto_admitted = stored_candidate is not None
        pareto_candidate_entry_id = stored_candidate.entry_id if stored_candidate else None
    pareto_after = pareto.cache.entries
    pareto_after_ids = {entry.entry_id for entry in pareto_after}
    pareto_evicted = evicted_entries(pareto_before, pareto_after_ids)
    for point in points:
        point["is_in_cache_after"] = (
            pareto_candidate_entry_id is not None
            if point["is_candidate"]
            else point["id"] in pareto_after_ids
        )

    def lookup_trace(result, threshold: float) -> dict:
        nearest = result.nearest_entry
        return {
            "hit": result.hit,
            "similarity": result.similarity,
            "threshold": threshold,
            "nearest_query": nearest.query_text if nearest else None,
            "nearest_entry_id": nearest.entry_id if nearest else None,
        }

    pareto_threshold = pareto_lookup.threshold_used
    return {
        "request": request.model_dump(exclude={"answer_text"}),
        "dataset_size": len(qa_pairs),
        "workload_index": target_index,
        "replay_index": request.trace_index,
        "query_source": query_source,
        "query": query,
        "candidate_answer_tokens": pareto.token_counter.count(answer),
        "answer_source": answer_source,
        "systems": {
            "scalm": {
                "lookup": lookup_trace(scalm_lookup, request.similarity_threshold),
                "admission": {
                    "status": (
                        "not_evaluated"
                        if scalm_lookup.hit
                        else ("admitted" if scalm_admitted else "rejected")
                    ),
                    "rank": scalm_pattern,
                    "reason": (
                        "Cache hit; no candidate admission."
                        if scalm_lookup.hit
                        else (
                            f"Cache was not full; SCALM admitted the {scalm_pattern}-rank candidate."
                            if not scalm_cache_was_full
                            else f"Cache was full; SCALM {'admitted' if scalm_admitted else 'rejected'} the {scalm_pattern}-rank candidate (only MID/HIGH pass)."
                        )
                    ),
                },
                "evicted": scalm_evicted,
                "cache_before_size": len(scalm_before),
                "cache_was_full": scalm_cache_was_full,
                "eviction_reason": (
                    "Rank-seeded LFU: lowest priority is evicted; oldest entry breaks ties."
                    if scalm_evicted
                    else None
                ),
                "cache_size": len(scalm_after),
                "cache": _cache_snapshot(scalm.cache, volatility_classifier),
            },
            "pareto": {
                "lookup": lookup_trace(pareto_lookup, pareto_threshold),
                "domain": domain_classifier.predict(query),
                "volatility_label": volatility_classifier.predict(query),
                "volatility": candidate_volatility,
                "admission": {
                    "status": (
                        "not_evaluated"
                        if pareto_lookup.hit
                        else ("admitted" if pareto_admitted else "rejected")
                    ),
                    "is_frontier": candidate_frontier,
                    "dominated_by": dominators,
                    "reason": (
                        "Cache hit; no candidate admission."
                        if pareto_lookup.hit
                        else (
                            "Cache is not full; current implementation admits unconditionally."
                            if not pareto_cache_was_full
                            else (
                                "Candidate is non-dominated and admitted."
                                if pareto_admitted
                                else "Candidate is dominated and rejected."
                            )
                        )
                    ),
                },
                "evicted": pareto_evicted,
                "cache_before_size": len(pareto_before),
                "cache_was_full": pareto_cache_was_full,
                "eviction_reason": (
                    (
                        "Current backend selects the lowest computed contribution from dominated entries."
                        if pareto_had_dominated_entries
                        else "Current backend selects the lowest-contribution prior frontier entry; the new candidate is retained."
                    )
                    if pareto_evicted
                    else None
                ),
                "cache_size": len(pareto_after),
                "cache": _cache_snapshot(pareto.cache, volatility_classifier),
                "plot_points": points,
            },
        },
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/experiments/run")
def run_experiment(request: ExperimentRequest) -> dict:
    return _run_experiment(request)


@app.post("/api/experiments/trace")
def trace_experiment(request: TraceRequest) -> dict:
    return _replay_trace(request)
