# What the Pareto Extension Should Actually Do

This document exists because the code answers "how is it implemented"
but nothing in the repo answers "what is it actually trying to
accomplish, and how would we know if it worked." Read this before
touching `backend/pareto/` — it's the spec the code should be checked
against, not a description of the code itself.

## 1. The problem, stated precisely

SCALM decides what to cache using **one number**: token-saving ratio
(TSR), ranked into HIGH/MID/LOW buckets. A full cache only admits
MID/HIGH. This has a specific, nameable failure mode:

> **The rank-volatility conflict**: the queries with the highest TSR are
> long, frequently-asked questions. But "frequently asked" and "answer
> changes over time or per-user" are not mutually exclusive — "what's
> today's weather," "what's my order status," and "summarize this
> quarter's earnings" can all have high TSR *and* be actively bad to
> cache long-term, because the correct answer changes. SCALM's
> single-objective rank has no way to see this: a high-TSR, high-risk
> entry looks identical to a high-TSR, safe entry.

The Pareto extension's entire justification rests on this conflict
being real and measurable. **If token-saving ratio and volatility turn
out to be uncorrelated in real data, there's no conflict to resolve —
SCALM's existing rank is already fine along that axis, and the correct
finding is "no meaningful trade-off exists here," not "our Pareto cache
does slightly different things."** This has NOT been checked yet (see
§5). Everything below is written as if the premise holds; treat that as
a working hypothesis, not an established fact.

## 2. What a genuine multi-objective cache admission mechanism requires

Not "compute a score," genuinely different things:

1. **Admission**: a candidate should be admitted if and only if no
   existing cache entry is at least as good in every objective and
   strictly better in one. This is Pareto dominance — not a weighted
   sum. A weighted sum (like JAS, see §4) collapses multiple objectives
   back into one number, which reintroduces the exact problem SCALM
   already has (a single ranked score), just with different inputs.
2. **Eviction**: when the cache is full and a genuinely non-dominated
   candidate needs to be admitted, something must be evicted. The
   correct target is the entry contributing the *least unique value* to
   the current non-dominated set — not the oldest, not the least
   recently used. Hypervolume contribution (§6 of `PARETO_AUDIT.md`)
   is the standard way to quantify this for a small number of
   objectives.
3. **The objectives must be at least partially independent.** If two
   objectives are strongly correlated, the Pareto frontier collapses
   toward a single point (whoever wins on the correlated pair wins on
   both), and the whole mechanism degenerates back into single-objective
   ranking — just with extra computation. This was **found to be true**
   in an earlier exploration using token-savings and *latency*
   (correlation ≈ 0.99, since longer answers take longer to generate).
   That's why this project uses **volatility**, not latency, as the
   second objective — but that substitution was a design decision made
   to avoid a known failure mode, not something verified against real
   data yet.

## 3. Why two objectives (token savings, volatility), not the original four

The original design (see early planning docs) considered four
objectives: token savings, latency, correctness, and compute cost.
What's actually implemented is two. This wasn't an oversight — it's a
deliberate scope reduction, but it was never written down explicitly
until now:

- **Latency** was dropped because it's strongly correlated with token
  savings (see §2) — including it would likely collapse the frontier,
  reproducing the exact failure mode this project exists to avoid.
- **Compute cost** is, for a fixed embedding model and cache
  architecture, mostly a function of token count too — likely another
  correlated objective, though this hasn't been explicitly checked.
- **Correctness** was dropped not because it's uninteresting, but
  because there's no way to measure it without either (a) a ground-truth
  answer to compare against, which doesn't exist for open-ended LLM
  responses, or (b) an expensive secondary LLM-as-judge call, which
  defeats the purpose of caching to save cost. **Volatility is a proxy
  for correctness risk** (a stable factual answer is unlikely to become
  wrong; a personal/temporal one is), chosen specifically because it's
  computable cheaply from the query text alone.

**This means the Pareto extension, as implemented, is really testing a
narrower and more specific hypothesis than the original four-objective
vision**: *"does explicitly modeling staleness risk alongside token
savings produce better cache decisions than token savings alone?"* That
is a legitimate, scoped-down research question. It should be stated as
such, not silently presented as the original four-objective plan having
been "completed."

## 4. JAS (Joint Admission Score) was removed — cold-start is unconditional by design

`pareto/admission.py`'s `JointAdmissionScore` (`TSR × (1 − α·volatility)`)
was a weighted score — exactly the single-number collapsing described in
§2 as the thing Pareto is supposed to avoid. It was originally
implemented as a **secondary, cold-start signal**: early in a cache's
life, there aren't enough entries to compute a meaningful frontier (a
frontier of 1-2 points is not informative), so a simple weighted score
seemed like a reasonable fallback for "is this worth admitting at all"
before the frontier machinery has anything to compare against.

**Resolution: JAS was removed.** It was never wired into `ParetoCache`,
and wiring it in would have reintroduced the exact single-objective
collapsing the Pareto approach exists to avoid. Cold-start admission is
**unconditional by design**, matching SCALM's own cold-start behavior:
with an empty or sparse cache there is no basis for comparison, so every
candidate is admitted until the cache is full, at which point pure
Pareto dominance takes over. The `JointAdmissionScore` class, its
isolated tests, and `pareto/admission.py` itself were deleted; the
cold-start rationale is documented in `pareto/cache.py`'s module
docstring.

## 5. The actual test of whether any of this is worth having

`scripts/audit_rank_volatility.py` computes the Spearman correlation
between SCALM's TSR rank and this project's volatility signal, on real
data. **This has been implemented but not yet run against real data.**
Now that a real MOSS file is available locally, this is the single most
important next step — more important than any further Pareto
implementation work, because it answers the question in §1: is there
actually a conflict here to resolve?

- **ρ < 0.3 (weak correlation)**: the premise holds. Token savings and
  volatility are meaningfully independent; a real trade-off exists; the
  Pareto mechanism is solving a real problem.
- **ρ > 0.7 (strong correlation)**: the premise likely does not hold on
  this data, at least not for this operationalization of volatility.
  The honest finding is "no meaningful conflict found in
  practice" — which is a legitimate, reportable negative result, not a
  failure of the implementation.
- **In between**: a real but modest trade-off exists; report the
  correlation value itself rather than only the categorical bucket.

## 6. Acceptance criteria — how to know this is actually done

Not "does it run," but:

1. `scripts/audit_rank_volatility.py` has been run on real (not
   synthetic) data, and the resulting correlation is reported and
   interpreted per §5 — whatever the result is.
2. The SCALMValidator frozen-after-warmup bug (see `PARETO_AUDIT.md` §3)
   is fixed, so the SCALM baseline being compared against is actually
   exercising its real rank-based mechanism, not a frozen warmup set.
3. `scripts/run_pareto.py` has been re-run on real data (real embeddings,
   real dataset, both bugs above fixed) and the SCALM-vs-Pareto
   comparison is reported as-is — including if Pareto loses on some
   metric, as it did in the synthetic run.
4. ~~JAS's role is resolved one way or the other (§4), not left
   ambiguous.~~ **Resolved: JAS was removed** (§4) — cold-start admission
   is unconditional by design, matching SCALM.
5. ~~A decision is made and documented on whether `ParetoCache` should use
   SCALM's clustering~~ **Resolved: intentional.** Pareto uses per-entry
   objectives (`-token_saving_proxy, volatility`), not pattern-level.
   Two entries in the same semantic cluster can receive different
   admission/eviction decisions — this is a design *feature*. SCALM
   groups queries and gives all members the same rank (coarse-grained);
   Pareto evaluates each entry independently (fine-grained). Adding
   pattern-level clustering would collapse Pareto back toward SCALM's
   single-score ranking, contradicting the multi-objective philosophy.
6. ~~The frontend's Pareto visualization either reflects the real backend
   objectives (token savings + volatility, minimizing convention) or is
   explicitly labeled as an illustrative mock, not connected to the
   Python backend's actual logic.~~ **Resolved: backend-aligned.** The
   frontend (`frontend/src/cacheData.js`, `frontend/src/App.jsx`) now
   uses the same 2 objectives (`-token_saving_proxy, volatility`) and
   minimizing convention as `backend/pareto/objectives.py` and
   `backend/pareto/dominance.py`. JAS was removed from the frontend too
   (it was already removed from the backend — see §4). The demo data is
   still illustrative (hardcoded), but the *logic* now mirrors the
   backend exactly.

Until these six are true, "Pareto extension implemented" should be
understood as "the mechanism exists and its logic is internally
tested," not "the mechanism has been shown to improve anything over
SCALM on real data."

All six items are now resolved (items 1-3 were completed as real-data
validation work on 2026-09-07; see `PARETO_AUDIT.md` sections 5b/5c for
the honest numbers):

1. `scripts/audit_rank_volatility_real.py` was run on real MOSS data:
   Spearman rho = -0.354 (5 clusters from 2000 queries) — directionally
   supportive of the premise, statistically weak.
2. The SCALMValidator frozen-after-warmup bug is fixed (see
   `PARETO_AUDIT.md` §3), so the SCALM baseline exercises its real
   rank-based mechanism.
3. `scripts/run_pareto_real.py` was run on real MOSS data: GPTCache
   0.318 / SCALM 0.185 / Pareto 0.235 hit ratio. Pareto beats SCALM on
   real data; GPTCache still leads on raw hit ratio. Reported as-is.
