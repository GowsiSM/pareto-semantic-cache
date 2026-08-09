// ─── src/cacheData.js ─────────────────────────────────────────────────

// ─── DEMO CACHE ENTRIES ───────────────────────────────────────────────────
export const INITIAL_CACHE = [
  {
    id: "C1",
    query: "What is machine learning?",
    response:
      "Machine learning is a branch of artificial intelligence that allows systems to learn and improve from experience without being explicitly programmed. It focuses on building applications that can access data and use it to learn for themselves.",
    embedding: [0.82, 0.41, -0.12, 0.67, 0.29, -0.54, 0.11, 0.78],
    tokenSaving: 82,
    latency: 80,
    correctness: 98,
    computeCost: 22,
    volatility: "stable",
    hits: 14,
  },
  {
    id: "C2",
    query: "Explain neural networks",
    response:
      "Neural networks are computing systems inspired by biological neural networks in animal brains. They consist of layers of interconnected nodes (neurons) that process information using connectionist approaches.",
    embedding: [0.74, 0.38, -0.09, 0.61, 0.33, -0.48, 0.17, 0.71],
    tokenSaving: 76,
    latency: 120,
    correctness: 99,
    computeCost: 31,
    volatility: "stable",
    hits: 9,
  },
  {
    id: "C3",
    query: "What is cloud computing?",
    response:
      "Cloud computing is the on-demand availability of computer system resources, especially data storage and computing power, without direct active management by the user.",
    embedding: [0.31, -0.22, 0.55, 0.18, 0.44, 0.62, -0.33, 0.25],
    tokenSaving: 65,
    latency: 90,
    correctness: 96,
    computeCost: 27,
    volatility: "stable",
    hits: 6,
  },
  {
    id: "C4",
    query: "What is deep learning?",
    response:
      "Deep learning is part of a broader family of machine learning methods based on artificial neural networks with representation learning. It uses multiple layers to progressively extract higher-level features from raw input.",
    embedding: [0.79, 0.44, -0.1, 0.65, 0.31, -0.51, 0.13, 0.75],
    tokenSaving: 79,
    latency: 95,
    correctness: 97,
    computeCost: 25,
    volatility: "stable",
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
export const LLM_RESPONSES = {
  "What is quantum computing?": {
    text: "Quantum computing harnesses quantum mechanical phenomena like superposition and entanglement to process information in fundamentally different ways than classical computers. Qubits can represent 0 and 1 simultaneously, enabling parallel computation at scale.",
    tokens: 312,
    latencyMs: 2140,
    computeCost: 28,
  },
  "How does blockchain work?": {
    text: "Blockchain is a distributed ledger technology where data is stored in blocks that are cryptographically linked. Each block contains a hash of the previous block, transaction data, and a timestamp, making the chain tamper-resistant.",
    tokens: 287,
    latencyMs: 1980,
    computeCost: 26,
  },
  default: {
    text: "This is a simulated LLM response generated for demonstration purposes. In production, this would be the actual response from an LLM API such as Gemini or GPT.",
    tokens: 250,
    latencyMs: 1800,
    computeCost: 24,
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
    tokenSaving: 91,
    latency: 74,
    correctness: 97,
    computeCost: 23,
    volatility: "stable",
  },
  "How does blockchain work?": {
    id: "C5",
    query: "How does blockchain work?",
    tokenSaving: 68,
    latency: 110,
    correctness: 95,
    computeCost: 34,
    volatility: "stable",
  },
};

// ─── PARETO FUNCTIONS ──────────────────────────────────────────────────────

/**
 * Pareto Skyline Computation
 * Each cache entry is a point in 4D objective space:
 *   tokenSaving   (higher is better)
 *   latency       (higher = more latency SAVED, so higher is better)
 *   correctness   (higher is better)
 *   computeCost   (lower is better → invert to: 100 - computeCost)
 *
 * Entry A dominates entry B if:
 *   A >= B on all four axes AND A > B on at least one.
 *
 * The Pareto frontier = all non-dominated entries.
 */

export function normalise(entry) {
  return {
    ...entry,
    // Invert computeCost so "higher is better" on every axis
    computeScore: 100 - entry.computeCost,
  };
}

export function dominates(a, b) {
  const aN = normalise(a);
  const bN = normalise(b);
  const axes = ["tokenSaving", "latency", "correctness", "computeScore"];
  const allGte = axes.every((ax) => aN[ax] >= bN[ax]);
  const someGt = axes.some((ax) => aN[ax] > bN[ax]);
  return allGte && someGt;
}

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
 * When |frontier| > budget, drop the entry with the lowest
 * product of all normalised objective values.
 */
export function pruneByHypervolume(frontier, budget) {
  if (frontier.length <= budget) return { kept: frontier, pruned: [] };
  const scored = frontier.map((e) => {
    const n = normalise(e);
    const score =
      (n.tokenSaving / 100) *
      (n.latency / 150) *
      (n.correctness / 100) *
      (n.computeScore / 100);
    return { ...e, hvScore: score };
  });
  scored.sort((a, b) => b.hvScore - a.hvScore);
  return {
    kept: scored.slice(0, budget),
    pruned: scored.slice(budget),
  };
}

/**
 * Joint admission score (SCALM-V formula):
 *   priority = tokenSaving × (1 − α × volatility_score)
 *
 * volatility_score: stable=0.1, temporal=0.7, personal=1.0
 */
export function jointAdmissionScore(entry, alpha = 0.5) {
  const volScore =
    { stable: 0.1, temporal: 0.7, personal: 1.0 }[entry.volatility] ?? 0.3;
  return entry.tokenSaving * (1 - alpha * volScore);
}
