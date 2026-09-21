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
from backend.embedding.mock_embedding import MockEmbeddingProvider
from backend.embedding.token_counter import SimpleTokenCounter
from backend.experiment.moss_loader import MOSSLoader
from backend.experiment.synthetic_dataset import generate_dataset
from backend.pareto.validator import ParetoValidator
from backend.scalm.validator import SCALMValidator
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


app = FastAPI(title="SemantiCache API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/experiments/run")
def run_experiment(request: ExperimentRequest) -> dict:
    return _run_experiment(request)
