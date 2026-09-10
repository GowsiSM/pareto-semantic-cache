import React, { useMemo, useState } from "react";

// ─── IMPORT NEW DATA AND FUNCTIONS ──────────────────────────────────────
import {
  INITIAL_CACHE,
  DEMO_QUERIES,
  LLM_RESPONSES,
  SIMILARITY_MAP,
  SIMILARITY_THRESHOLD,
  CANDIDATE_ENTRIES,
  dominates,
  computeParetoFrontier,
  pruneByHypervolume,
  computeAdaptiveThreshold,
  classifyDomain,
} from "./cacheData";

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
  const [queryDomain, setQueryDomain] = useState("general");
  const [adaptiveThreshold, setAdaptiveThreshold] = useState(SIMILARITY_THRESHOLD);
  const [systemMetrics, setSystemMetrics] = useState(null);

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
      // Classify domain for this query (mirrors backend/domain_classifier.py)
      const domain = classifyDomain(query);
      setQueryDomain(domain);
      addLog(`🧠 Semantic embedding generated. Domain classified as: ${domain}`);
    }

    if (steps[next] === "search") {
      const bestMatchScore = bestMatch?.match ?? 0;
      // Compute adaptive threshold (mirrors backend/pareto/threshold.py)
      const vol = bestMatch?.volatility ?? 0.0;
      const thresh = computeAdaptiveThreshold(queryDomain, vol);
      setAdaptiveThreshold(thresh);
      addLog(
        `🔍 Similarity search completed. Best similarity: ${bestMatchScore.toFixed(2)}. Adaptive threshold: ${thresh.toFixed(3)}`,
      );
    }

    if (steps[next] === "decision") {
      const matchScore = bestMatch?.match ?? 0;
      // Use adaptive threshold instead of fixed (backend-aligned)
      const isHit = matchScore >= adaptiveThreshold;
      setResult({
        hit: isHit,
        matched: bestMatch,
        candidate: null,
      });
      addLog(
        isHit
          ? `✅ CACHE HIT (similarity ${matchScore.toFixed(2)} ≥ threshold ${adaptiveThreshold.toFixed(3)}) — cached response returned.`
          : `❌ CACHE MISS (similarity ${matchScore.toFixed(2)} < threshold ${adaptiveThreshold.toFixed(3)}) — sending to LLM.`,
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
            domain: classifyDomain(query),
            hits: 1,
          };
        } else {
          // Generate a new candidate
          newCandidate = {
            id: `C${cache.length + 1}`,
            query,
            response: LLM_RESPONSES.default.text,
            embedding: [0.5, 0.3, -0.1, 0.4, 0.2, -0.3, 0.1, 0.5],
            tokenSaving: Math.round(200 + Math.random() * 150),
            volatility: Math.round(Math.random() * 100) / 100,
            domain: classifyDomain(query),
            hits: 0,
          };
        }

        setResult((prev) => ({ ...prev, candidate: newCandidate }));
        addLog(`🤖 LLM response generated. Domain: ${newCandidate.domain}. Candidate cache entry created.`);
      }
    }

    if (steps[next] === "evaluation") {
      const tsr = candidate?.tokenSaving ?? 0;
      const vol = candidate?.volatility ?? 0;
      const domain = classifyDomain(candidate?.query ?? query);
      addLog(
        `📊 Candidate evaluated: TSR_proxy=${tsr}, volatility=${vol.toFixed(2)}, domain=${domain}`,
      );
      setShowDetailedMetrics(true);

      // Compute backend-aligned system metrics (cumulative across simulation)
      setSystemMetrics((prev) => {
        const totalQ = (prev?.total_queries ?? 0) + 1;
        const hits = (prev?.hits ?? 0) + (result?.hit ? 1 : 0);
        const misses = (prev?.misses ?? 0) + (result?.hit ? 0 : 1);
        const staleHits = (prev?.stale_hits ?? 0) + (vol > 0.5 ? 1 : 0);
        const falseHits = (prev?.false_hits ?? 0) + 0; // no false hits in demo
        const tokensSaved = (prev?.tokens_saved ?? 0) + (result?.hit ? tsr : 0);
        const totalTokens = (prev?.total_tokens ?? 0) + tsr;
        return {
          total_queries: totalQ,
          hits,
          misses,
          stale_hits: staleHits,
          false_hits: falseHits,
          tokens_saved: tokensSaved,
          total_tokens: totalTokens,
          hit_rate: hits / totalQ,
          token_saving_ratio: totalTokens > 0 ? tokensSaved / totalTokens : 0,
          staleness_rate: hits > 0 ? staleHits / hits : 0,
          false_hit_rate: hits > 0 ? falseHits / hits : 0,
        };
      });
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
    const domain = classifyDomain(query);
    setQueryDomain(domain);
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

      // Compute adaptive threshold (backend-aligned)
      const vol = bestMatchEntry?.volatility ?? 0.0;
      const thresh = computeAdaptiveThreshold(domain, vol);
      setAdaptiveThreshold(thresh);

      const isHit = bestMatchEntry?.match >= thresh;

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
            domain: classifyDomain(query),
            hits: 0,
          };
        } else {
          newCandidate = {
            id: `C${cache.length + 1}`,
            query,
            response: LLM_RESPONSES.default.text,
            embedding: [0.5, 0.3, -0.1, 0.4, 0.2, -0.3, 0.1, 0.5],
            tokenSaving: 250,
            volatility: 0.15,
            domain: classifyDomain(query),
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
    // Classify domain and compute adaptive threshold
    const domain = classifyDomain(demoQuery.text);
    setQueryDomain(domain);
    setAdaptiveThreshold(computeAdaptiveThreshold(domain, 0.0));
    // Reset simulation state but KEEP the query
    setStepIndex(0);
    setResult(null);
    setLogs([]);
    setShowDetailedMetrics(false);
    setSystemMetrics(null);
    addLog(`📝 Selected: "${demoQuery.text}" [domain: ${domain}]`);
  }

  // ─── RENDER ───────────────────────────────────────────────────────────
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">RESEARCH DEMO</p>
          <h1>Pareto-Based Semantic Cache Management</h1>
          <p className="subtitle">
            Frontend visualization — backend-aligned Pareto logic (2 objectives, minimizing)
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
              <p>SCALM embedding + domain classifier → adaptive threshold → Pareto frontier admission</p>
            </div>
          </div>

          <div className="flow">
            {[
              ["embedding", "Embed + Domain", "SCALM+"],
              ["search", "Similarity Search", "SCALM"],
              ["decision", "Adaptive Threshold", "PROPOSED"],
              ["inference", "LLM Inference", "Existing"],
              ["evaluation", "Multi-Objective Eval", "PROPOSED"],
              ["pareto", "Pareto Skyline", "PROPOSED"],
              ["admission", "Hypervolume Eviction", "PROPOSED"],
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
                <strong>{bestMatch ? bestMatch.match.toFixed(3) : "—"}</strong>
              </div>
              <div className="state-box">
                <span>Adaptive Threshold</span>
                <strong>{adaptiveThreshold.toFixed(3)}</strong>
                <small className="threshold-note">
                  base {SIMILARITY_THRESHOLD} {queryDomain !== "general" ? `+ ${queryDomain}` : ""}
                </small>
              </div>
            </div>

            <div className="match-list">
              {searchResults.map((item) => (
                <div className="match-row" key={item.id}>
                  <div>
                    <strong>{item.id}</strong>
                    <span>{item.query}</span>
                    {item.domain && (
                      <span className="domain-badge">{item.domain}</span>
                    )}
                  </div>
                  <div className="similarity">
                    <span>{item.match.toFixed(3)}</span>
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
                  <span className="domain-badge">
                    {candidate.domain ?? queryDomain}
                  </span>
                  <span className="volatility-badge">
                    vol {candidate.volatility?.toFixed(2) ?? "0.00"}
                  </span>
                </div>
                <div className="metrics">
                  <Metric
                    label="Token Saving Proxy"
                    value={candidate.tokenSaving}
                    unit=" tokens"
                  />
                  <Metric
                    label="Volatility"
                    value={candidate.volatility?.toFixed(2) ?? "0.00"}
                  />
                  {showDetailedMetrics && (
                    <>
                      <Metric label="Hits" value={candidate.hits || 0} />
                      <Metric
                        label="Domain"
                        value={candidate.domain ?? queryDomain}
                      />
                    </>
                  )}
                </div>

                {/* Backend-aligned evaluation metrics */}
                {showDetailedMetrics && (
                  <div className="eval-metrics">
                    <h4>System Metrics (backend-aligned)</h4>
                    <div className="metrics">
                      <Metric
                        label="Cache Hit Ratio"
                        value={
                          systemMetrics
                            ? (systemMetrics.hit_rate * 100).toFixed(1)
                            : "—"
                        }
                        unit="%"
                      />
                      <Metric
                        label="Token Saving Ratio"
                        value={
                          systemMetrics
                            ? (systemMetrics.token_saving_ratio * 100).toFixed(1)
                            : "—"
                        }
                        unit="%"
                      />
                      <Metric
                        label="Staleness Rate"
                        value={
                          systemMetrics
                            ? (systemMetrics.staleness_rate * 100).toFixed(1)
                            : "—"
                        }
                        unit="%"
                      />
                      <Metric
                        label="False Hit Rate"
                        value={
                          systemMetrics
                            ? (systemMetrics.false_hit_rate * 100).toFixed(1)
                            : "—"
                        }
                        unit="%"
                      />
                    </div>
                  </div>
                )}

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
              <span>· Adaptive threshold per domain+volatility</span>
            </div>
          </section>
        </div>

        {/* Pareto Skyline — backend-aligned 2-objective plot */}
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>5. Pareto Skyline</h2>
              <p>
                Non-dominated entries on two objectives: token saving proxy
                (↑ higher = more tokens saved) and volatility (↓ lower = safer
                to cache). A dominates B when A is better on at least one
                objective and no worse on the other.
              </p>
            </div>
            <div className="legend">
              <span className="dot" /> Pareto-optimal
            </div>
          </div>

          <div className="pareto-area">
            <div className="axis-y">Token Saving Proxy ↑</div>
            <div className="chart">
              <div className="gridline g1" />
              <div className="gridline g2" />
              <div className="gridline g3" />
              {paretoWithCandidate.frontier.map((item) => {
                const maxSaving = Math.max(
                  ...paretoWithCandidate.frontier.map((e) => e.tokenSaving),
                  1,
                );
                // X-axis: volatility (0 = left, 1 = right)
                const x = Math.min(92, Math.max(8, item.volatility * 90 + 5));
                // Y-axis: tokenSaving (higher = higher)
                const y = Math.min(
                  90,
                  Math.max(8, (item.tokenSaving / maxSaving) * 85),
                );
                return (
                  <div
                    className={`point ${candidate?.id === item.id ? "candidate-point" : ""}`}
                    key={item.id}
                    style={{ left: `${x}%`, bottom: `${y}%` }}
                    title={`${item.id}: saving=${item.tokenSaving}, volatility=${item.volatility?.toFixed(2)}`}
                  >
                    <span>{item.id}</span>
                  </div>
                );
              })}
              <div className="axis-x">Low Volatility ← → High Volatility</div>
            </div>
          </div>

          <div className="frontier-list">
            {paretoWithCandidate.frontier.map((item) => (
              <div className="frontier-item" key={item.id}>
                <strong>{item.id}</strong>
                <span>Saving: {item.tokenSaving}</span>
                <span>Volatility: {item.volatility?.toFixed(2) ?? "0.00"}</span>
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
                    {item.domain && (
                      <span className="domain-badge">{item.domain}</span>
                    )}
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
        <span>SCALM semantic cache baseline</span>
        <span>•</span>
        <span>Pareto multi-objective admission (2 objectives: TSR, volatility)</span>
        <span>•</span>
        <span>Adaptive threshold (domain + volatility aware)</span>
        <span>•</span>
        <span>Hypervolume-constrained eviction</span>
      </footer>
    </div>
  );
}

export default App;
