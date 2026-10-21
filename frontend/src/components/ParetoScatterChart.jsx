// ─── ParetoScatterChart.jsx ──────────────────────────────────────────────────
// Interactive Pareto trade-off visualization.
// Two objectives (minimizing convention):
//   X: volatility   0.0 (stable) → 1.0 (volatile)   — lower is better
//   Y: tokenSaving  higher = more tokens saved       — higher is better
//
// Shows both Pareto-optimal and dominated entries so the contrast is clear.

import React, { useState } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

// ─── Custom dot shapes ────────────────────────────────────────────────────────
function FrontierDot(props) {
  const { cx, cy, payload, onClick, selected } = props;
  const r = selected ? 10 : 7;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill="var(--pareto-color)"
      stroke={selected ? "var(--fg)" : "white"}
      strokeWidth={selected ? 2.5 : 2}
      style={{ cursor: "pointer" }}
      onClick={() => onClick && onClick(payload)}
      tabIndex={0}
      role="button"
      aria-label={`Frontier entry ${payload.id}: saving=${payload.tokenSaving}, volatility=${payload.volatility?.toFixed(2)}`}
      onKeyDown={(e) => e.key === "Enter" && onClick && onClick(payload)}
    />
  );
}

function DominatedDot(props) {
  const { cx, cy, payload, onClick, selected } = props;
  const r = selected ? 9 : 6;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill="none"
      stroke="var(--muted-2)"
      strokeWidth={selected ? 2.5 : 1.5}
      style={{ cursor: "pointer" }}
      onClick={() => onClick && onClick(payload)}
      tabIndex={0}
      role="button"
      aria-label={`Dominated entry ${payload.id}: saving=${payload.tokenSaving}, volatility=${payload.volatility?.toFixed(2)}`}
      onKeyDown={(e) => e.key === "Enter" && onClick && onClick(payload)}
    />
  );
}

function CandidateDot(props) {
  const { cx, cy, payload, onClick } = props;
  return (
    <g onClick={() => onClick && onClick(payload)} style={{ cursor: "pointer" }}>
      <circle cx={cx} cy={cy} r={9} fill="var(--accent)" stroke="white" strokeWidth={2} />
      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fill="white" fontSize={8} fontWeight={700}>
        NEW
      </text>
    </g>
  );
}

// ─── Custom Tooltip ───────────────────────────────────────────────────────────
function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="point-detail" style={{ minWidth: 180 }}>
      <strong style={{ fontSize: 13 }}>{d.id}</strong>
      <div style={{ marginTop: 6, fontSize: 12, color: "var(--muted)" }}>
        <div>Token saving: <strong style={{ color: "var(--fg)" }}>{d.tokenSaving}</strong></div>
        <div>Volatility: <strong style={{ color: "var(--fg)" }}>{d.volatility?.toFixed(3)}</strong></div>
        {d.domain && <div>Domain: <strong style={{ color: "var(--fg)" }}>{d.domain}</strong></div>}
      </div>
    </div>
  );
}

// ─── Point detail panel ───────────────────────────────────────────────────────
function PointDetail({ entry, isFrontier, dominators }) {
  if (!entry) return null;
  return (
    <div className="point-detail">
      <h4>{entry.id} — {entry.query?.slice(0, 50)}{entry.query?.length > 50 ? "…" : ""}</h4>
      <div className="point-detail-grid">
        <div className="point-detail-item">
          <span className="point-detail-label">Token Saving Proxy</span>
          <span className="point-detail-value">{entry.tokenSaving}</span>
        </div>
        <div className="point-detail-item">
          <span className="point-detail-label">Volatility</span>
          <span className="point-detail-value">{entry.volatility?.toFixed(3)}</span>
        </div>
        <div className="point-detail-item">
          <span className="point-detail-label">Domain</span>
          <span className="point-detail-value">{entry.domain ?? "general"}</span>
        </div>
        <div className="point-detail-item">
          <span className="point-detail-label">Pareto Status</span>
          <span className="point-detail-value" style={{ color: isFrontier ? "var(--pareto-color)" : "var(--muted)" }}>
            {isFrontier ? "Non-dominated ✓" : "Dominated ✗"}
          </span>
        </div>
      </div>
      {!isFrontier && dominators.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--muted)" }}>
          Dominated by: {dominators.map((d) => d.id).join(", ")}
        </div>
      )}
      <div style={{ marginTop: 8, fontSize: 12, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        <strong>Admission:</strong>{" "}
        {isFrontier
          ? "✅ Admitted (non-dominated under SPARC policy)"
          : "❌ Rejected (dominated by an existing entry)"}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export function ParetoScatterChart({ frontier, dominated, candidate }) {
  const [selected, setSelected] = useState(null);

  const allEntries = [...(frontier ?? []), ...(dominated ?? [])];
  const selectedIsFrontier = frontier?.some((e) => e.id === selected?.id);
  const dominators = selected
    ? frontier?.filter((f) => {
        // f dominates selected if f is ≤ on both objectives and < on one
        const fObj = [-f.tokenSaving, f.volatility ?? 0];
        const sObj = [-selected.tokenSaving, selected.volatility ?? 0];
        return (
          fObj[0] <= sObj[0] &&
          fObj[1] <= sObj[1] &&
          (fObj[0] < sObj[0] || fObj[1] < sObj[1])
        );
      })
    : [];

  const maxSaving = Math.max(...allEntries.map((e) => e.tokenSaving), candidate?.tokenSaving ?? 0, 1);

  const frontierData = (frontier ?? []).map((e) => ({
    ...e,
    x: e.volatility ?? 0,
    y: e.tokenSaving,
  }));
  const dominatedData = (dominated ?? []).map((e) => ({
    ...e,
    x: e.volatility ?? 0,
    y: e.tokenSaving,
  }));
  const candidateData = candidate
    ? [{ ...candidate, x: candidate.volatility ?? 0, y: candidate.tokenSaving }]
    : [];

  return (
    <div>
      {/* Callout explanation */}
      <div className="callout pareto-callout" style={{ marginBottom: 16 }}>
        A candidate can <em>save many tokens</em> and still be a poor cache choice if its answer is
        likely to become outdated. The Pareto frontier captures all entries where <em>no other entry
        is simultaneously better on both objectives</em>.
      </div>

      <div className="pareto-area" style={{ height: 320 }}>
        <div className="axis-y">Token Saving Proxy ↑</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 12, right: 24, bottom: 32, left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                type="number"
                dataKey="x"
                domain={[0, 1]}
                name="Volatility"
                tick={{ fontSize: 11, fill: "var(--muted)" }}
                label={{ value: "← Safer to Cache    More Volatile →", position: "insideBottom", offset: -16, fontSize: 11, fill: "var(--muted)" }}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[0, maxSaving * 1.1]}
                name="Token Saving"
                tick={{ fontSize: 11, fill: "var(--muted)" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "var(--muted)" }}
                verticalAlign="top"
              />
              <Scatter
                name="Pareto frontier"
                data={frontierData}
                shape={(props) => (
                  <FrontierDot
                    {...props}
                    selected={selected?.id === props.payload?.id}
                    onClick={setSelected}
                  />
                )}
                legendType="circle"
                fill="var(--pareto-color)"
              />
              <Scatter
                name="Dominated"
                data={dominatedData}
                shape={(props) => (
                  <DominatedDot
                    {...props}
                    selected={selected?.id === props.payload?.id}
                    onClick={setSelected}
                  />
                )}
                legendType="circle"
                fill="var(--muted-2)"
              />
              {candidateData.length > 0 && (
                <Scatter
                  name="Candidate (new)"
                  data={candidateData}
                  shape={(props) => <CandidateDot {...props} onClick={setSelected} />}
                  legendType="circle"
                  fill="var(--accent)"
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Point inspector */}
      {selected ? (
        <PointDetail
          entry={selected}
          isFrontier={selectedIsFrontier}
          dominators={dominators ?? []}
        />
      ) : (
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
          Click any point to inspect its objectives and admission decision.
        </p>
      )}

      {/* Accessible text table fallback */}
      <details style={{ marginTop: 16 }}>
        <summary style={{ fontSize: 11, color: "var(--muted)", cursor: "pointer" }}>
          All entries (accessible list)
        </summary>
        <table className="results-table" style={{ marginTop: 8, fontSize: 12 }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Query</th>
              <th>Token Saving</th>
              <th>Volatility</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {[...(frontier ?? []), ...(dominated ?? [])].map((e) => (
              <tr key={e.id}>
                <td>{e.id}</td>
                <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {e.query}
                </td>
                <td>{e.tokenSaving}</td>
                <td>{e.volatility?.toFixed(3)}</td>
                <td style={{ color: frontier?.some((f) => f.id === e.id) ? "var(--pareto-color)" : "var(--muted)" }}>
                  {frontier?.some((f) => f.id === e.id) ? "Non-dominated" : "Dominated"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
