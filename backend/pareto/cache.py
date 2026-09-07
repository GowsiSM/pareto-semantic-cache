"""
ParetoCache: the actual multi-objective semantic cache.

PROJECT-PROPOSED EXTENSION, replacing SCALM's single-score rank-based
admission/eviction with genuine multi-objective (Pareto) decisions over
two objectives: token-saving proxy (maximize) and volatility (minimize).
See objectives.py for the exact conversion, dominance.py/frontier.py for
the Pareto machinery, and hypervolume.py for capacity-constrained
pruning. None of this is from the SCALM paper -- see each module's
docstring for what would otherwise be a false attribution.

DESIGN, mirroring ScalmCache's shape so the two are drop-in comparable
in an experiment harness:

  lookup(): identical mechanics to ScalmCache -- embed, search, but with
  an ADAPTIVE threshold (via AdaptiveThresholdAdapter, domain + volatility
  aware) instead of ScalmCache's fixed 0.90.

  store():
    - Cold cache (not yet full): admit unconditionally, matching SCALM's
      own cold-start behavior -- there's no basis for Pareto comparison
      with an empty/sparse cache. (A weighted admission score like JAS
      was considered for this phase but deliberately NOT used: it
      collapses the two objectives back into one number, which is the
      single-objective ranking the Pareto approach exists to avoid. See
      PARETO_DESIGN.md section 4.)
    - Full cache: compute the candidate's objective vector, add it to the
      existing entries' objective vectors, and compute the Pareto
      frontier of that combined set. If the candidate is NOT in the
      frontier (i.e. strictly dominated by at least one existing entry
      in both objectives), reject it -- there's no scenario where
      admitting it improves the cache's Pareto-optimal set.
    - If the candidate IS in the frontier: admit it, then check whether
      the cache now needs an eviction. Evict the entry with the lowest
      hypervolume contribution among currently DOMINATED entries first
      (an entry that's neither in the frontier, nor now needed for
      capacity, should be evicted before touching frontier entries).
      If no dominated victim exists (rare: frontier == entire cache),
      fall back to lowest hypervolume contribution among the whole
      frontier.

KNOWN LIMITATION: recomputing the full frontier on every store() call
against a full cache is O(capacity) per call (frontier computation is
O(n^2) via dominance.py's current implementation) -- fine for the cache
sizes this project targets (dozens to low hundreds), not something to
scale past that without revisiting dominance.py's algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.classifier.domain_classifier import DomainClassifier
from backend.classifier.volatility_classifier import VolatilityClassifier
from backend.domain.entities import CacheEntry
from backend.interfaces.protocols import EmbeddingProvider, TokenCounter, VectorStore
from backend.pareto.dominance import pareto_frontier
from backend.pareto.hypervolume import compute_hypervolume_contributions
from backend.pareto.objectives import objective_vector
from backend.pareto.threshold import AdaptiveThresholdAdapter

# A reference point guaranteed dominated by (i.e. worse than) any
# realistic candidate under the minimizing convention: since
# objective[0] = -token_count and token_count >= 0, the WORST possible
# value for objective[0] is 0.0 (a hypothetical zero-token answer), not
# a large negative number -- an earlier version of this constant had
# the sign backwards and was caught by test_cache.py raising a
# ValueError from hypervolume.py's own dominance check.
_REFERENCE_TOKEN_CEILING = 0.0
_REFERENCE_VOLATILITY_CEILING = 1.0


@dataclass
class ParetoLookupResult:
    hit: bool
    entry: Optional[CacheEntry]
    similarity: Optional[float]
    threshold_used: Optional[float] = None


class ParetoCache:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        token_counter: TokenCounter,
        capacity: int,
        similarity_threshold: float = 0.90,
        volatility_classifier: Optional[VolatilityClassifier] = None,
        domain_classifier: Optional[DomainClassifier] = None,
        threshold_adapter: Optional[AdaptiveThresholdAdapter] = None,
    ) -> None:
        self._embedding = embedding_provider
        self._store = vector_store
        self._tokens = token_counter
        self._capacity = capacity
        self._volatility_clf = volatility_classifier or VolatilityClassifier()
        self._domain_clf = domain_classifier or DomainClassifier()
        self._threshold_adapter = threshold_adapter or AdaptiveThresholdAdapter(
            base_threshold=similarity_threshold
        )
        self._id_counter = 0
        self._hit_count = 0
        self._miss_count = 0

    def lookup(self, query_text: str) -> ParetoLookupResult:
        query_embedding = self._embedding.embed(query_text)
        candidates = self._store.search(query_embedding, top_k=1)

        domain = self._domain_clf.predict(query_text)
        volatility = self._volatility_clf.volatility_score(query_text)
        threshold = self._threshold_adapter.compute(domain=domain, volatility=volatility)

        if not candidates:
            self._miss_count += 1
            return ParetoLookupResult(hit=False, entry=None, similarity=None, threshold_used=threshold)

        entry, similarity = candidates[0]
        if similarity >= threshold:
            entry.record_hit()
            self._hit_count += 1
            return ParetoLookupResult(hit=True, entry=entry, similarity=similarity, threshold_used=threshold)

        self._miss_count += 1
        return ParetoLookupResult(hit=False, entry=None, similarity=similarity, threshold_used=threshold)

    def store(self, query_text: str, answer_text: str) -> Optional[CacheEntry]:
        embedding = self._embedding.embed(query_text)
        query_tokens = self._tokens.count(query_text)
        answer_tokens = self._tokens.count(answer_text)
        volatility = self._volatility_clf.volatility_score(query_text)

        self._id_counter += 1
        entry_id = f"pareto_{self._id_counter}"

        candidate = CacheEntry(
            entry_id=entry_id,
            query_text=query_text,
            answer_text=answer_text,
            embedding=embedding,
            pattern_id=None,  # ParetoCache doesn't use SCALM's clustering/patterns
            query_token_count=query_tokens,
            answer_token_count=answer_tokens,
        )

        cache_is_full = self._store.size() >= self._capacity
        if not cache_is_full:
            self._store.add(candidate)
            return candidate

        return self._admit_to_full_cache(candidate, volatility)

    def _admit_to_full_cache(self, candidate: CacheEntry, candidate_volatility: float) -> Optional[CacheEntry]:
        existing_entries = self._store.all_entries()
        existing_volatilities = [
            self._volatility_clf.volatility_score(e.query_text) for e in existing_entries
        ]

        all_entries = existing_entries + [candidate]
        all_objectives = [
            objective_vector(e, v)
            for e, v in zip(existing_entries, existing_volatilities)
        ] + [objective_vector(candidate, candidate_volatility)]

        frontier_values = pareto_frontier(all_objectives)
        candidate_objective = all_objectives[-1]

        if candidate_objective not in frontier_values:
            return None  # candidate is dominated by an existing entry -- reject

        # Candidate is admitted. Now evict someone to make room.
        frontier_indices = {i for i, obj in enumerate(all_objectives) if obj in frontier_values}
        dominated_indices = [i for i in range(len(all_entries)) if i not in frontier_indices]

        if dominated_indices:
            # Evict the dominated entry with the lowest hypervolume
            # contribution first (least unique value among the "already
            # inferior" entries).
            dominated_points = [all_objectives[i] for i in dominated_indices]
            reference = (_REFERENCE_TOKEN_CEILING, _REFERENCE_VOLATILITY_CEILING)
            contributions = compute_hypervolume_contributions(dominated_points, reference)
            victim_local_idx = min(range(len(dominated_indices)), key=lambda i: contributions[i])
            victim_global_idx = dominated_indices[victim_local_idx]
        else:
            # No dominated entries exist (frontier == entire cache);
            # fall back to evicting the lowest-hypervolume-contribution
            # frontier member EXCLUDING the just-admitted candidate.
            frontier_indices_excl_candidate = [i for i in frontier_indices if i != len(all_entries) - 1]
            frontier_points = [all_objectives[i] for i in frontier_indices_excl_candidate]
            reference = (_REFERENCE_TOKEN_CEILING, _REFERENCE_VOLATILITY_CEILING)
            contributions = compute_hypervolume_contributions(frontier_points, reference)
            victim_local_idx = min(range(len(frontier_points)), key=lambda i: contributions[i])
            victim_global_idx = frontier_indices_excl_candidate[victim_local_idx]

        victim_entry = all_entries[victim_global_idx]
        self._store.remove(victim_entry.entry_id)
        self._store.add(candidate)
        return candidate

    @property
    def size(self) -> int:
        return self._store.size()

    @property
    def hit_rate(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        total = self._hit_count + self._miss_count
        return {
            "size": self.size,
            "capacity": self._capacity,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": self.hit_rate,
            "total_queries": total,
            "is_full": self.size >= self._capacity,
        }
