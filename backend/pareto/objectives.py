"""
Objective vector construction for the Pareto extension.

PROJECT-PROPOSED EXTENSION — the SCALM paper has no multi-objective
formulation; this defines how THIS project turns a cache candidate into
the two-objective vector used by pareto/dominance.py.

dominance.py uses a MINIMIZING convention (lower is better in every
coordinate). Our two objectives are:

  1. token_saving_proxy — HIGHER is better (bigger answers cached =
     more tokens saved per hit). We negate it to fit the minimizing
     convention: objective[0] = -token_saving_proxy.
  2. volatility — LOWER is better (a stable, unlikely-to-go-stale answer
     is safer to cache long-term). Used as-is: objective[1] = volatility.

So a candidate with high token savings and low volatility gets a low
(good) objective vector under the minimizing convention, e.g. (-500, 0.0)
dominates (-100, 0.65).

WHY TOKEN COUNT AS THE SAVINGS PROXY: the paper's real token_saving_ratio
(Eq. 4) is a property of a whole workload replay (tokens saved by hits /
total tokens), not a single candidate in isolation. For a per-candidate
admission/eviction DECISION, we need a proxy available at store() time,
before we know how many future hits it will get. Using the candidate's
own token count (query + answer) as that proxy is a simple, documented
design choice (D) — it assumes "answers that would cost more tokens to
regenerate are more valuable to cache," which is directionally
reasonable but not validated against real reuse data yet.
"""
from __future__ import annotations

from backend.domain.entities import CacheEntry


def compute_token_saving_proxy(answers: list[str]) -> float:
    """
    Average whitespace-token count across a list of answers, used as a
    simple token-saving proxy for a semantic pattern's members (see
    scripts/audit_rank_volatility.py) or for a single candidate answer
    (pass a one-item list).
    """
    if not answers:
        return 0.0
    counts = [len(a.split()) for a in answers]
    return sum(counts) / len(counts)


def entry_token_saving_proxy(entry: CacheEntry) -> float:
    """Token-saving proxy for a single CacheEntry, using its own token counts."""
    return float(entry.total_token_count)


def objective_vector(entry: CacheEntry, volatility: float) -> tuple[float, float]:
    """
    Build the minimizing-convention objective vector for one cache entry:
    (-token_saving_proxy, volatility).
    """
    bounded_volatility = max(0.0, min(1.0, volatility))
    return (-entry_token_saving_proxy(entry), bounded_volatility)
