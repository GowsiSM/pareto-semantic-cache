# backend/scalm/validator.py
from typing import List, Tuple, Dict, Optional, Any
from backend.cache.scalm_cache import ScalmCache
from backend.cache.admission import RankBasedAdmissionPolicy
from backend.cache.eviction import RankSeededLFUEviction
from backend.embedding.token_counter import SimpleTokenCounter
from backend.vector_store.in_memory import InMemoryVectorStore
from backend.scalm.clustering import DBSCANRoundClustering
from backend.domain.entities import PatternRank, SemanticPattern

class SCALMValidator:
    """
    Validate SCALM implementation against MOSS dataset.
    Reproduces the paper's experimental setup.

    KNOWN LIMITATION (found during the Pareto-extension audit, not fixed
    here since it's a separate scope of work): every store() call below
    -- including ones AFTER the warmup phase -- constructs a
    SemanticPattern with hardcoded rank=PatternRank.LOW. Combined with
    RankBasedAdmissionPolicy's real rule (full cache admits only
    MID/HIGH rank), this means once the cache fills during warmup, NO
    further entry can ever be admitted -- the cache is effectively
    frozen at the warmup set for the rest of the run. This means any
    previously-reported hit rate from this validator reflects how often
    post-warmup queries happen to match the fixed warmup set, not
    SCALM's actual clustering-driven rank admission (which needs a real
    batch clustering + token-saving-ratio ranking pass -- see
    backend/scalm/clustering.py's DBSCANRoundClustering, which exists
    but isn't wired into this validator's per-query store() calls).
    Worth fixing before treating this validator's numbers as a faithful
    SCALM reproduction.
    """
    
    def __init__(
        self,
        capacity: int = 100,
        similarity_threshold: float = 0.90,
        embedding_provider: Optional[Any] = None,
    ):
        self.capacity = capacity
        self.threshold = similarity_threshold
        if embedding_provider is None:
            # Only import/construct the real (network-dependent) model
            # if the caller didn't inject one -- lets this validator run
            # in environments without Hugging Face access, e.g. for
            # logic validation with MockEmbeddingProvider.
            from backend.embedding.sentence_transformer_provider import (
                SentenceTransformerEmbeddingProvider,
            )

            embedding_provider = SentenceTransformerEmbeddingProvider()
        self.embedding_provider = embedding_provider
        self.token_counter = SimpleTokenCounter()
        self.cache = ScalmCache(
            embedding_provider=self.embedding_provider,
            vector_store=InMemoryVectorStore(),
            token_counter=self.token_counter,
            admission_policy=RankBasedAdmissionPolicy(),
            eviction_policy=RankSeededLFUEviction(),
            capacity=capacity,
            similarity_threshold=similarity_threshold
        )
        self.stats = {
            "hits": 0,
            "misses": 0,
            "tokens_saved": 0,
            "total_tokens": 0,
            "llm_calls": 0
        }
    
    def run(self, qa_pairs: List[Tuple[str, str]], warmup_count: int = 100) -> Dict:
        """
        Run SCALM validation on QA pairs.
        
        Args:
            qa_pairs: List of (query, response) tuples
            warmup_count: Number of entries to warm up cache with
        
        Returns:
            Dict with metrics
        """
        # Step 1: Warm up cache (cold start)
        for i, (query, response) in enumerate(qa_pairs[:warmup_count]):
            pattern = SemanticPattern(
                pattern_id=f"warm_{i}",
                round_index=1,
                centroid=[0.0] * 384,
                rank=PatternRank.LOW  # Cold cache admits LOW
            )
            self.cache.store(query, response, pattern)
        
        # Step 2: Process remaining queries
        for query, response in qa_pairs[warmup_count:]:
            # Count tokens for this response
            response_tokens = self.token_counter.count(response)
            self.stats["total_tokens"] += response_tokens
            
            # Check cache
            result = self.cache.lookup(query)
            
            if result.hit:
                self.stats["hits"] += 1
                self.stats["tokens_saved"] += response_tokens
            else:
                self.stats["misses"] += 1
                self.stats["llm_calls"] += 1
                # Store in cache (simulate LLM generation)
                pattern = SemanticPattern(
                    pattern_id=f"miss_{self.stats['llm_calls']}",
                    round_index=1,
                    centroid=[0.0] * 384,
                    rank=PatternRank.LOW
                )
                self.cache.store(query, response, pattern)
        
        # Step 3: Compute metrics
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        token_saving_rate = self.stats["tokens_saved"] / self.stats["total_tokens"] if self.stats["total_tokens"] > 0 else 0
        
        return {
            "hit_rate": hit_rate,
            "token_saving_rate": token_saving_rate,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total_queries": total,
            "llm_calls": self.stats["llm_calls"],
            "tokens_saved": self.stats["tokens_saved"],
            "total_tokens": self.stats["total_tokens"]
        }
    
    def reset(self):
        """Reset cache and stats."""
        self.cache = ScalmCache(
            embedding_provider=self.embedding_provider,
            vector_store=InMemoryVectorStore(),
            token_counter=self.token_counter,
            admission_policy=RankBasedAdmissionPolicy(),
            eviction_policy=RankSeededLFUEviction(),
            capacity=self.capacity,
            similarity_threshold=self.threshold
        )
        self.stats = {
            "hits": 0,
            "misses": 0,
            "tokens_saved": 0,
            "total_tokens": 0,
            "llm_calls": 0
        }