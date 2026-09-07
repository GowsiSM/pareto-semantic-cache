// ─── src/cacheData.js ─────────────────────────────────────────────────
//
// This file provides illustrative demo data for the frontend visualization.
// The Pareto logic here is BACKEND-ALIGNED: it uses the same 2 objectives
// and minimizing convention as backend/pareto/objectives.py.
//
// Objectives (minimizing convention — lower is better):
//   1. tokenSavingProxy = total_token_count (query + answer tokens)
//      Higher → more tokens saved per hit.  Negated for minimization.
//   2. volatility = 0.0 (stable) … 1.0 (highly volatile)
//      Higher → more likely to go stale, worse to cache.
//
// Dominance: entry A dominates B when A's objective vector is <= B's
// on every coordinate and strictly < on at least one.
//
// NOTE: This is illustrative data, not computed from the real backend.
// The frontend's job is to show the Pareto mechanism — the real numbers
// come from scripts/run_pareto.py.

// ─── DEMO CACHE ENTRIES ───────────────────────────────────────────────────
// Each entry mirrors a backend CacheEntry with:
//   - tokenSaving:  total_token_count (query + answer tokens, whitespace-split)
//   - volatility:   0.0 (stable) … 1.0 (highly volatile)
export const INITIAL_CACHE = [
  {
    id: "C1",
    query: "What is machine learning?",
    response:
      "Machine learning is a branch of artificial intelligence that allows systems to learn and improve from experience without being explicitly programmed. It focuses on building applications that can access data and use it to learn for themselves.",
    embedding: [0.82, 0.41, -0.12, 0.67, 0.29, -0.54, 0.11, 0.78],
    tokenSaving: 82,
    volatility: 0.1,
    hits: 14,
  },
  {
    id: "C2",
    query: "Explain neural networks",
    response:
      "Neural networks are computing systems inspired by biological neural networks in animal brains. They consist of layers of interconnected nodes (neurons) that process information using connectionist approaches.",
    embedding: [0.74, 0.38, -0.09, 0.61, 0.33, -0.48, 0.17, 0.71],
    tokenSaving: 76,
    volatility: 0.3,
    hits: 9,
  },
  {
    id: "C3",
    query: "What is cloud computing?",
    response:
      "Cloud computing is the on-demand availability of computer system resources, especially data storage and computing power, without direct active management by the user.",
    embedding: [0.31, -0.22, 0.55, 0.18, 0.44, 0.62, -0.33, 0.25],
    tokenSaving: 65,
    volatility: 0.0,
    hits: 6,
  },
  {
    id: "C4",
    query: "What is deep learning?",
    response:
      "Deep learning is part of a broader family of machine learning methods based on artificial neural networks with representation learning. It uses multiple layers to progressively extract higher-level features from raw input.",
    embedding: [0.79, 0.44, -0.1, 0.65, 0.31, -0.51, 0.13, 0.75],
    tokenSaving: 79,
    volatility: 0.2,
    hits: 11,
  },
];

// ─── PRESET DEMO QUERIES ──────────────────────────────────────────────────
export const DEMO_QUERIES = [
  {
    text: "Explain machine learning in simple words",
    expectedHit: true,
    matchId: "C1",
    note: "Semantic HIT — different wording, same meaning as C1",
  },
  {
    text: "What are neural networks?",
    expectedHit: true,
    matchId: "C2",
    note: "Semantic HIT — matches C2",
  },
  {
    text: "What is quantum computing?",
    expectedHit: false,
    matchId: null,
    note: "MISS — no similar entry exists. LLM will be called.",
  },
  {
    text: "Tell me about deep learning",
    expectedHit: true,
    matchId: "C4",
    note: "Semantic HIT — matches C4",
  },
  {
    text: "How does blockchain work?",
    expectedHit: false,
    matchId: null,
    note: "MISS — triggers full Pareto evaluation pipeline",
  },
];

// ─── SIMULATED LLM RESPONSES (for cache misses) ───────────────────────────
// In production these come from the real LLM API; here we use
// illustrative token counts that feed into token_saving_proxy.
export const LLM_RESPONSES = {
  "What is quantum computing?": {
    text: "Quantum computing harnesses quantum mechanical phenomena like superposition and entanglement to process information in fundamentally different ways than classical computers. Qubits can represent 0 and 1 simultaneously, enabling parallel computation at scale.",
    tokens: 312,
  },
  "How does blockchain work?": {
    text: "Blockchain is a distributed ledger technology where data is stored in blocks that are cryptographically linked. Each block contains a hash of the previous block, transaction data, and a timestamp, making the chain tamper-resistant.",
    tokens: 287,
  },
  default: {
    text: "This is a simulated LLM response generated for demonstration purposes. In production, this would be the actual response from an LLM API such as Gemini or GPT.",
    tokens: 250,
  },
};

// ─── SIMILARITY MAP (deterministic — same query always gives same scores) ─
export const SIMILARITY_MAP = {
  "explain machine learning in simple words": {
    C1: 0.94,
    C2: 0.41,
    C3: 0.18,
    C4: 0.67,
  },
  "what are neural networks?": { C1: 0.48, C2: 0.91, C3: 0.22, C4: 0.55 },
  "what is quantum computing?": { C1: 0.21, C2: 0.19, C3: 0.38, C4: 0.23 },
  "tell me about deep learning": { C1: 0.71, C2: 0.58, C3: 0.14, C4: 0.89 },
  "how does blockchain work?": { C1: 0.15, C2: 0.12, C3: 0.29, C4: 0.17 },
};

export const SIMILARITY_THRESHOLD = 0.85;

// ─── CANDIDATE ENTRIES for cache misses (deterministic) ───────────────────
export const CANDIDATE_ENTRIES = {
  "What is quantum computing?": {
    id: "C5",
    query: "What is quantum computing?",
    tokenSaving: 312,
    volatility: 0.0,
  },
  "How does blockchain work?": {
    id: "C5",
    query: "How does blockchain work?",
    tokenSaving: 287,
    volatility: 0.4,
  },
};

// ─── PARETO FUNCTIONS ──────────────────────────────────────────────────────
//
// These functions are BACKEND-ALIGNED with backend/pareto/dominance.py
// and backend/pareto/objectives.py.
//
// Objectives (MINIMIZING convention — lower is better in every coordinate):
//   obj[0] = -tokenSaving   (negated so higher tokenSaving → lower value)
//   obj[1] = volatility     (0.0 = stable, 1.0 = highly volatile)
//
// Dominance: A dominates B iff A <= B on every objective and A < B on
// at least one.

/**
 * Build the minimizing-convention objective vector for one entry.
 * Mirrors backend/pareto/objectives.py::objective_vector().
 */
function objectiveVector(entry) {
  const boundedVol = Math.max(0, Math.min(1, entry.volatility ?? 0));
  return [-entry.tokenSaving, boundedVol];
}

/**
 * Pareto dominance test (minimizing convention).
 * Mirrors backend/pareto/dominance.py::dominates().
 */
export function dominates(a, b) {
  const aObj = objectiveVector(a);
  const bObj = objectiveVector(b);
  const allLte = aObj[0] <= bObj[0] && aObj[1] <= bObj[1];
  const someLt = aObj[0] < bObj[0] || aObj[1] < bObj[1];
  return allLte && someLt;
}

/**
 * Compute the Pareto frontier (non-dominated set) from a list of entries.
 * Returns { frontier, dominated } where each entry carries its obj vector.
 */
export function computeParetoFrontier(entries) {
  const frontier = [];
  const dominated = [];

  for (const candidate of entries) {
    const isDominated = entries.some(
      (other) => other.id !== candidate.id && dominates(other, candidate),
    );
    if (isDominated) {
      dominated.push(candidate);
    } else {
      frontier.push(candidate);
    }
  }

  return { frontier, dominated };
}

/**
 * Hypervolume contribution proxy (simplified):
 * When |frontier| > budget, drop the entry with the lowest hypervolume
 * contribution (product of objective values in the minimising space,
 * scaled to [0,1]).
 */
export function pruneByHypervolume(frontier, budget) {
  if (frontier.length <= budget) return { kept: frontier, pruned: [] };

  const maxSaving = Math.max(...frontier.map((e) => e.tokenSaving), 1);
  const scored = frontier.map((e) => {
    const obj = objectiveVector(e);
    // Normalise to [0,1] in minimising space: -obj[0]/maxSaving in [0,1], obj[1] in [0,1]
    const normSaving = (-obj[0]) / maxSaving;  // higher saving → higher normSaving
    const normVol = obj[1];                     // lower volatility → lower normVol
    // HV proxy: product of normalised values (lower is worse → prune lowest)
    const hvScore = normSaving * (1 - normVol);
    return { ...e, hvScore };
  });
  scored.sort((a, b) => b.hvScore - a.hvScore);
  return {
    kept: scored.slice(0, budget),
    pruned: scored.slice(budget),
  };
}

/**
 * Note: JointAdmissionScore (JAS) has been removed from the backend
 * because it collapses two objectives into a single weighted sum,
 * which contradicts the Pareto philosophy.  See PARETO_DESIGN.md §4.
 */
