import React, { useMemo, useState } from "react";

// ─── IMPORT NEW DATA AND FUNCTIONS ──────────────────────────────────────
import {
  INITIAL_CACHE,
  DEMO_QUERIES,
  LLM_RESPONSES,
  SIMILARITY_MAP,
  SIMILARITY_THRESHOLD,
  CANDIDATE_ENTRIES,
  normalise,
  dominates,
  computeParetoFrontier,
  pruneByHypervolume,
  jointAdmissionScore,
} from "./cacheData"; // You'll need to create this file with the exported data

// ─── STEP PIPELINE ──────────────────────────────────────────────────────
const steps = [
  "idle",
  "embedding",
  "search",
  "decision",
  "inference",
  "evaluation",
  "pareto",
  "admission",
  "complete",
];

// ─── METRIC COMPONENT ──────────────────────────────────────────────────
function Metric({ label, value, unit = "" }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>
        {value}
        {unit}
      </strong>
    </div>
  );
}

// ─── APP ──────────────────────────────────────────────────────────────
function App() {
  // ─── STATE ──────────────────────────────────────────────────────────
  const [query, setQuery] = useState(DEMO_QUERIES[0].text);
  const [cache, setCache] = useState(INITIAL_CACHE);
  const [stepIndex, setStepIndex] = useState(0);
  const [result, setResult] = useState(null);
  const [logs, setLogs] = useState([]);
  const [selectedDemoQuery, setSelectedDemoQuery] = useState(DEMO_QUERIES[0]);
  const [showDetailedMetrics, setShowDetailedMetrics] = useState(false);

  const step = steps[stepIndex];

  // ─── COMPUTED VALUES ────────────────────────────────────────────────
  const searchResults = useMemo(() => {
    const queryLower = query.toLowerCase();
    // Use SIMILARITY_MAP if available, else fallback to simple matching
    const similarities = SIMILARITY_MAP[queryLower] || {};

    return cache
      .map((item) => {
        const match = similarities[item.id] ?? 0.0;
        return {
          ...item,
          match,
        };
      })
      .sort((a, b) => b.match - a.match);
  }, [cache, query]);

  const bestMatch = searchResults[0];
  const candidate = result?.candidate;
  const hit = result?.hit;

  // Compute Pareto frontier for current cache
  const paretoResult = useMemo(() => {
    return computeParetoFrontier(cache);
  }, [cache]);

  // Include candidate in Pareto analysis if it exists
  const allEntriesForPareto = useMemo(() => {
    if (!candidate) return cache;
    return [...cache, candidate];
  }, [cache, candidate]);

  const paretoWithCandidate = useMemo(() => {
    return computeParetoFrontier(allEntriesForPareto);
  }, [allEntriesForPareto]);

  // ─── LOGGING ──────────────────────────────────────────────────────────
  function addLog(message) {
    setLogs((prev) =>
      [`${new Date().toLocaleTimeString()} — ${message}`, ...prev].slice(0, 8),
    );
  }

  // ─── SIMULATION CONTROLS ──────────────────────────────────────────────
  function startSimulation() {
    setStepIndex(1);
    setResult(null);
    addLog("📥 Query received. Generating semantic embedding.");
  }

  function nextStep() {
    if (stepIndex === 0) {
      startSimulation();
      return;
    }

    const next = Math.min(stepIndex + 1, steps.length - 1);
    setStepIndex(next);

    if (steps[next] === "embedding") {
      addLog("🧠 Semantic embedding generated.");
    }

    if (steps[next] === "search") {
      const bestMatchScore = bestMatch?.match ?? 0;
      addLog(
        `🔍 Similarity search completed. Best similarity: ${bestMatchScore.toFixed(2)}.`,
      );
    }

    if (steps[next] === "decision") {
      const matchScore = bestMatch?.match ?? 0;
      const isHit = matchScore >= SIMILARITY_THRESHOLD;
      setResult({
        hit: isHit,
        matched: bestMatch,
        candidate: null,
      });
      addLog(
        isHit
          ? "✅ CACHE HIT — cached response can be returned."
          : "❌ CACHE MISS — sending query to LLM.",
      );
    }

    if (steps[next] === "inference") {
      if (!hit) {
        // Create candidate from predefined data or generate one
        let newCandidate;
        const queryLower = query.toLowerCase();

        // Check if we have a predefined candidate
        const predefinedCandidate = CANDIDATE_ENTRIES[query];
        if (predefinedCandidate) {
          newCandidate = {
            ...predefinedCandidate,
            response: LLM_RESPONSES[query]?.text || LLM_RESPONSES.default.text,
            embedding: [0.5, 0.3, -0.1, 0.4, 0.2, -0.3, 0.1, 0.5],
            volatility: "stable",
            hits: 1,
          };
        } else {
          // Generate a new candidate
          newCandidate = {
            id: `C${cache.length + 1}`,
            query,
            response: LLM_RESPONSES.default.text,
            embedding: [0.5, 0.3, -0.1, 0.4, 0.2, -0.3, 0.1, 0.5],
            tokenSaving: Math.round(70 + Math.random() * 27),
            latency: Math.round(70 + Math.random() * 120),
            correctness: Math.round(92 + Math.random() * 8),
            computeCost: Math.round(20 + Math.random() * 40),
            volatility: "stable",
            hits: 0,
          };
        }

        setResult((prev) => ({ ...prev, candidate: newCandidate }));
        addLog("🤖 LLM response generated. Candidate cache entry created.");
      }
    }

    if (steps[next] === "evaluation") {
      const score = candidate ? jointAdmissionScore(candidate) : 0;
      addLog(
        `📊 Candidate evaluated on token savings, latency, correctness and compute cost. Joint score: ${score.toFixed(2)}`,
      );
      setShowDetailedMetrics(true);
    }

    if (steps[next] === "pareto") {
      const frontierSize = paretoWithCandidate.frontier.length;
      addLog(
        `🏔️ Pareto skyline calculated. ${frontierSize} non-dominated entries identified.`,
      );
    }

    if (steps[next] === "admission") {
      if (candidate) {
        const { frontier, dominated } = computeParetoFrontier([
          ...cache,
          candidate,
        ]);
        const isAdmitted = frontier.some((x) => x.id === candidate.id);

        if (isAdmitted) {
          // Apply cache budget (max 5 entries for demo)
          const budget = 5;
          const { kept, pruned } = pruneByHypervolume(frontier, budget);
          setCache(kept);
          addLog(
            `✅ ${candidate.id} admitted — it is non-dominated and fits within cache budget.`,
          );
        } else {
          addLog(
            `❌ ${candidate.id} rejected — it is dominated by an existing entry.`,
          );
        }
      }
    }

    if (steps[next] === "complete") {
      addLog("✅ Cache state updated. Simulation complete.");
    }
  }

  function reset() {
    setCache(INITIAL_CACHE);
    setStepIndex(0);
    setResult(null);
    setLogs([]);
    setShowDetailedMetrics(false);
  }

  // ─── FULL DEMO RUN ──────────────────────────────────────────────────
  function runFullDemo() {
    reset();
    setTimeout(() => setStepIndex(1), 100);
    setTimeout(() => setStepIndex(2), 500);
    setTimeout(() => {
      const queryLower = query.toLowerCase();
      const similarities = SIMILARITY_MAP[queryLower] || {};
      const bestMatchEntry = cache
        .map((item) => ({
          ...item,
          match: similarities[item.id] ?? 0.0,
        }))
        .sort((a, b) => b.match - a.match)[0];

      const isHit = bestMatchEntry?.match >= SIMILARITY_THRESHOLD;

      if (isHit) {
        setResult({ hit: true, matched: bestMatchEntry, candidate: null });
        addLog("✅ CACHE HIT — response returned without LLM inference.");
        setStepIndex(3);
        setTimeout(() => setStepIndex(8), 700);
      } else {
        // Create candidate from predefined data or generate one
        let newCandidate;
        const predefinedCandidate = CANDIDATE_ENTRIES[query];
        if (predefinedCandidate) {
          newCandidate = {
            ...predefinedCandidate,
            response: LLM_RESPONSES[query]?.text || LLM_RESPONSES.default.text,
            embedding: [0.5, 0.3, -0.1, 0.4, 0.2, -0.3, 0.1, 0.5],
            volatility: "stable",
            hits: 0,
          };
        } else {
          newCandidate = {
            id: `C${cache.length + 1}`,
            query,
            response: LLM_RESPONSES.default.text,
            embedding: [0.5, 0.3, -0.1, 0.4, 0.2, -0.3, 0.1, 0.5],
            tokenSaving: 94,
            latency: 75,
            correctness: 99,
            computeCost: 24,
            volatility: "stable",
            hits: 0,
          };
        }

        setResult({
          hit: false,
          matched: bestMatchEntry,
          candidate: newCandidate,
        });
        setStepIndex(3);
        setTimeout(() => setStepIndex(4), 500);
        setTimeout(() => setStepIndex(5), 900);
        setTimeout(() => setStepIndex(6), 1300);
        setTimeout(() => {
          setStepIndex(7);
          const { frontier } = computeParetoFrontier([...cache, newCandidate]);
          const budget = 5;
          const { kept } = pruneByHypervolume(frontier, budget);
          setCache(kept);
          addLog(
            `✅ ${newCandidate.id} evaluated and admitted if non-dominated.`,
          );
        }, 1700);
        setTimeout(() => setStepIndex(8), 2200);
      }
    }, 900);
  }

  // ─── PRESET QUERY SELECTOR ──────────────────────────────────────────
  // ─── PRESET QUERY SELECTOR ──────────────────────────────────────────
  function selectDemoQuery(demoQuery) {
    setSelectedDemoQuery(demoQuery);
    setQuery(demoQuery.text);
    // Reset simulation state but KEEP the query
    setStepIndex(0);
    setResult(null);
    setLogs([]);
    setShowDetailedMetrics(false);
    addLog(`📝 Selected: "${demoQuery.text}"`);
  }

  // ─── RENDER ───────────────────────────────────────────────────────────
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">RESEARCH DEMO</p>
          <h1>Pareto-Based Semantic Cache Management</h1>
          <p className="subtitle">
            Frontend visualization of the proposed SCALM extension
          </p>
        </div>
        <div className="badge">DEMO ONLY · SIMULATED BACKEND</div>
      </header>

      <main>
        {/* Query Panel */}
        <section className="query-panel card">
          <div className="panel-title">
            <div>
              <h2>1. Submit Query</h2>
              <p>Visualize how a query moves through the semantic cache.</p>
            </div>
          </div>

          <div className="query-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter a query..."
            />
            <button onClick={runFullDemo}>Run Demo</button>
            <button className="secondary" onClick={reset}>
              Reset
            </button>
          </div>

          <div className="presets">
            {DEMO_QUERIES.map((demoQuery) => (
              <button
                key={demoQuery.text}
                onClick={() => selectDemoQuery(demoQuery)}
                className={
                  selectedDemoQuery.text === demoQuery.text ? "active" : ""
                }
              >
                {demoQuery.text}
                <small>{demoQuery.expectedHit ? "✓ HIT" : "✗ MISS"}</small>
              </button>
            ))}
          </div>
        </section>

        {/* Pipeline */}
        <section className="pipeline card">
          <div className="section-heading">
            <div>
              <h2>2. Processing Pipeline</h2>
              <p>SCALM foundation → proposed Pareto-based cache decision</p>
            </div>
          </div>

          <div className="flow">
            {[
              ["embedding", "Query Embedding", "SCALM"],
              ["search", "Similarity Search", "SCALM"],
              ["decision", "Hit / Miss", "SCALM"],
              ["inference", "LLM Inference", "Existing"],
              ["evaluation", "Multi-Objective Evaluation", "PROPOSED"],
              ["pareto", "Pareto Skyline", "PROPOSED"],
              ["admission", "Admission / Eviction", "PROPOSED"],
              ["complete", "Updated Cache", "CACHE"],
            ].map(([key, title, type], i) => (
              <React.Fragment key={key}>
                <div
                  className={`flow-node ${step === key || steps.indexOf(key) < stepIndex ? "active" : ""} ${type === "PROPOSED" ? "proposed" : ""}`}
                >
                  <span className="node-number">{i + 1}</span>
                  <strong>{title}</strong>
                  <small>{type}</small>
                </div>
                {i < 7 && <span className="arrow">→</span>}
              </React.Fragment>
            ))}
          </div>
        </section>

        {/* Grid: Cache + Evaluation */}
        <div className="grid">
          <section className="card">
            <div className="section-heading">
              <div>
                <h2>3. Semantic Cache Layer</h2>
                <p>
                  Similarity search determines whether the request is a hit or
                  miss.
                </p>
              </div>
            </div>

            <div className="cache-state">
              <div
                className={`state-box ${hit ? "hit" : hit === false ? "miss" : ""}`}
              >
                <span>Cache Status</span>
                <strong>
                  {hit === true ? "HIT" : hit === false ? "MISS" : "WAITING"}
                </strong>
              </div>
              <div className="state-box">
                <span>Best Similarity</span>
                <strong>{bestMatch ? bestMatch.match.toFixed(2) : "—"}</strong>
              </div>
              <div className="state-box">
                <span>Threshold</span>
                <strong>{SIMILARITY_THRESHOLD}</strong>
              </div>
            </div>

            <div className="match-list">
              {searchResults.map((item) => (
                <div className="match-row" key={item.id}>
                  <div>
                    <strong>{item.id}</strong>
                    <span>{item.query}</span>
                  </div>
                  <div className="similarity">
                    <span>{item.match.toFixed(2)}</span>
                    <div className="bar">
                      <i style={{ width: `${item.match * 100}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="section-heading">
              <div>
                <h2>4. Multi-Objective Evaluation</h2>
                <p>
                  Candidate cache entries are evaluated across four objectives.
                </p>
              </div>
            </div>

            {candidate ? (
              <div className="candidate">
                <div className="candidate-title">
                  <strong>{candidate.id}</strong>
                  <span>Candidate Cache Entry</span>
                  <span className="volatility-badge">
                    {candidate.volatility}
                  </span>
                </div>
                <div className="metrics">
                  <Metric
                    label="Token Saving"
                    value={candidate.tokenSaving}
                    unit="%"
                  />
                  <Metric
                    label="Latency"
                    value={candidate.latency}
                    unit=" ms"
                  />
                  <Metric
                    label="Correctness"
                    value={candidate.correctness}
                    unit="%"
                  />
                  <Metric label="Compute Cost" value={candidate.computeCost} />
                  {showDetailedMetrics && (
                    <>
                      <Metric
                        label="Joint Score"
                        value={jointAdmissionScore(candidate).toFixed(2)}
                        unit=""
                      />
                      <Metric
                        label="Hits"
                        value={candidate.hits || 0}
                        unit=""
                      />
                    </>
                  )}
                </div>
                {candidate.response && (
                  <div className="llm-response">
                    <strong>LLM Response:</strong>
                    <p>{candidate.response}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty">
                <span>Waiting for a cache miss...</span>
                <small>Choose a MISS query to see candidate evaluation.</small>
              </div>
            )}

            <div className="objective-key">
              <span>↑ Higher is better</span>
              <span>↓ Lower is better</span>
            </div>
          </section>
        </div>

        {/* Pareto Skyline */}
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>5. Pareto Skyline</h2>
              <p>
                Non-dominated entries represent different optimal trade-offs.
              </p>
            </div>
            <div className="legend">
              <span className="dot" /> Pareto-optimal
            </div>
          </div>

          <div className="pareto-area">
            <div className="axis-y">Token Saving ↑</div>
            <div className="chart">
              <div className="gridline g1" />
              <div className="gridline g2" />
              <div className="gridline g3" />
              {paretoWithCandidate.frontier.map((item) => {
                const x = Math.min(92, Math.max(8, 100 - item.latency / 2.2));
                const y = Math.min(90, Math.max(8, item.tokenSaving - 5));
                return (
                  <div
                    className={`point ${candidate?.id === item.id ? "candidate-point" : ""}`}
                    key={item.id}
                    style={{ left: `${x}%`, bottom: `${y}%` }}
                    title={`${item.id}: ${item.tokenSaving}% savings, ${item.latency}ms`}
                  >
                    <span>{item.id}</span>
                  </div>
                );
              })}
              <div className="axis-x">Lower Latency ← → Higher Latency</div>
            </div>
          </div>

          <div className="frontier-list">
            {paretoWithCandidate.frontier.map((item) => (
              <div className="frontier-item" key={item.id}>
                <strong>{item.id}</strong>
                <span>Token {item.tokenSaving}%</span>
                <span>{item.latency} ms</span>
                <span>Correctness {item.correctness}%</span>
                <span>Cost {item.computeCost}</span>
                <span>Hits: {item.hits || 0}</span>
                <div className="frontier-badge">NON-DOMINATED</div>
              </div>
            ))}
          </div>
        </section>

        {/* Bottom Grid: Cache State + Logs */}
        <div className="grid bottom">
          <section className="card">
            <div className="section-heading">
              <div>
                <h2>6. Cache State</h2>
                <p>Entries retained after Pareto-based selection.</p>
              </div>
              <div className="cache-stats">
                <span>Total: {cache.length} entries</span>
                <span>Pareto: {paretoResult.frontier.length} entries</span>
              </div>
            </div>
            <div className="cache-table">
              {cache.map((item) => (
                <div className="cache-entry" key={item.id}>
                  <div>
                    <strong>{item.id}</strong>
                    <span>{item.query}</span>
                    <span className="hits-badge">Hits: {item.hits || 0}</span>
                  </div>
                  <span
                    className={`tag ${paretoResult.frontier.some((f) => f.id === item.id) ? "pareto" : "dominated"}`}
                  >
                    {paretoResult.frontier.some((f) => f.id === item.id)
                      ? "PARETO"
                      : "DOMINATED"}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="section-heading">
              <div>
                <h2>Activity Log</h2>
                <p>Useful for explaining the demo to reviewers.</p>
              </div>
            </div>
            <div className="logs">
              {logs.length ? (
                logs.map((log, i) => <div key={i}>{log}</div>)
              ) : (
                <span>No activity yet.</span>
              )}
            </div>
          </section>
        </div>
      </main>

      <footer>
        <span>SCALM-inspired semantic cache workflow</span>
        <span>•</span>
        <span>Proposed Pareto-based admission visualization</span>
        <span>•</span>
        <span>
          4D Objective Space: Token Savings ↑ Latency ↓ Correctness ↑ Compute
          Cost ↓
        </span>
      </footer>
    </div>
  );
}

export default App;
