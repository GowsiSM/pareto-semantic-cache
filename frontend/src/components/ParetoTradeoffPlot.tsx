import { useState } from "react";
import type { SystemDecisionTrace } from "../api/types";

interface ParetoTradeoffPlotProps {
  trace: SystemDecisionTrace;
}

export function ParetoTradeoffPlot({ trace }: ParetoTradeoffPlotProps) {
  const points = trace.plot_points ?? [];
  const candidate = points.find((point) => point.is_candidate);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    points.find((point) => point.id === selectedId) ??
    candidate ??
    points.find((point) => point.id === trace.lookup.nearest_entry_id) ??
    points[0];
  const selectedDominators = selected
    ? selected.dominated_by.map((id) => points.find((point) => point.id === id)).filter((point) => point !== undefined)
    : [];
  const maxSaving = Math.max(1, ...points.map((point) => point.token_saving_proxy));
  const chart = { left: 74, right: 786, top: 26, bottom: 332 };
  const x = (volatility: number) =>
    chart.left + Math.max(0, Math.min(1, volatility)) * (chart.right - chart.left);
  const y = (saving: number) =>
    chart.bottom - (saving / maxSaving) * (chart.bottom - chart.top);
  const frontierPath = points
    .filter((point) => point.is_frontier)
    .sort((left, right) => left.volatility - right.volatility)
    .map((point) => `${x(point.volatility)},${y(point.token_saving_proxy)}`)
    .join(" ");

  return (
    <div className="tradeoff-plot">
      <div className="plot-explainer">
        <strong>Why two objectives?</strong>
        <span>
          High token savings do not make a volatile answer safe to keep. The
          frontier preserves entries that are not worse on both objectives.
        </span>
      </div>

      {points.length === 0 ? (
        <p className="empty-state">No cache entries were available for this replay event.</p>
      ) : (
        <>
          <div className="plot-frame">
            <svg
              viewBox="0 0 820 405"
              role="img"
              aria-labelledby="pareto-plot-title pareto-plot-description"
            >
              <title id="pareto-plot-title">SPARC cache entries by volatility and token savings</title>
              <desc id="pareto-plot-description">
                The horizontal axis is volatility, where lower is safer. The
                vertical axis is token-saving proxy, where higher is better.
                Filled circles are non-dominated entries, hollow squares are
                dominated entries, and a diamond is the candidate being evaluated.
              </desc>
              {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
                <g key={tick}>
                  <line
                    x1={x(tick)}
                    x2={x(tick)}
                    y1={chart.top}
                    y2={chart.bottom}
                    className="plot-gridline"
                  />
                  <text x={x(tick)} y={chart.bottom + 23} textAnchor="middle" className="plot-tick">
                    {tick.toFixed(2)}
                  </text>
                </g>
              ))}
              {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
                const value = Math.round(maxSaving * fraction);
                return (
                  <g key={fraction}>
                    <line
                      x1={chart.left}
                      x2={chart.right}
                      y1={y(value)}
                      y2={y(value)}
                      className="plot-gridline"
                    />
                    <text x={chart.left - 10} y={y(value) + 4} textAnchor="end" className="plot-tick">
                      {value}
                    </text>
                  </g>
                );
              })}
              <line x1={chart.left} x2={chart.right} y1={chart.bottom} y2={chart.bottom} className="plot-axis" />
              <line x1={chart.left} x2={chart.left} y1={chart.top} y2={chart.bottom} className="plot-axis" />
              {frontierPath && (
                <polyline points={frontierPath} className="frontier-line" aria-hidden="true" />
              )}
              {points.map((point) => {
                const pointX = x(point.volatility);
                const pointY = y(point.token_saving_proxy);
                const isSelected = selected?.id === point.id;
                const markerClass = point.is_candidate
                  ? "plot-point candidate-point"
                  : point.is_frontier
                    ? "plot-point frontier-point"
                    : "plot-point dominated-point";
                return (
                  <g
                    key={point.id}
                    className={markerClass}
                    role="button"
                    tabIndex={0}
                    aria-label={`${point.query}; ${point.is_candidate ? "candidate" : point.is_frontier ? "frontier entry" : "dominated entry"}; token-saving proxy ${point.token_saving_proxy}; volatility ${point.volatility.toFixed(2)}`}
                    onClick={() => setSelectedId(point.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedId(point.id);
                      }
                    }}
                  >
                    {point.is_candidate ? (
                      <path
                        d={`M ${pointX} ${pointY - 9} L ${pointX + 9} ${pointY} L ${pointX} ${pointY + 9} L ${pointX - 9} ${pointY} Z`}
                        className={isSelected ? "point-shape is-selected" : "point-shape"}
                      />
                    ) : point.is_frontier ? (
                      <circle
                        cx={pointX}
                        cy={pointY}
                        r={isSelected ? 9 : 7}
                        className={isSelected ? "point-shape is-selected" : "point-shape"}
                      />
                    ) : (
                      <rect
                        x={pointX - (isSelected ? 8 : 6)}
                        y={pointY - (isSelected ? 8 : 6)}
                        width={isSelected ? 16 : 12}
                        height={isSelected ? 16 : 12}
                        className={isSelected ? "point-shape is-selected" : "point-shape"}
                      />
                    )}
                  </g>
                );
              })}
              <text x={(chart.left + chart.right) / 2} y="386" textAnchor="middle" className="plot-axis-label">
                Volatility: lower is safer ← · → higher risk
              </text>
              <text
                x="18"
                y={(chart.top + chart.bottom) / 2}
                textAnchor="middle"
                className="plot-axis-label"
                transform={`rotate(-90 18 ${(chart.top + chart.bottom) / 2})`}
              >
                Token-saving proxy: higher is better
              </text>
            </svg>
          </div>

          <div className="plot-legend" aria-label="Plot legend">
            <span><i className="legend-circle" /> Pareto frontier</span>
            <span><i className="legend-square" /> Dominated</span>
            <span><i className="legend-diamond" /> Candidate</span>
          </div>

          <div className="plot-inspector">
            <div>
              <span className="eyebrow">Selected point</span>
              <h3>{selected?.query ?? "Select an entry"}</h3>
              {selected && (
                <p>
                  {selected.is_candidate
                    ? `Admission: ${trace.admission.status} (${trace.cache_was_full ? "cache full" : "cache not full"}). Pareto status: ${selected.is_frontier ? "frontier" : "dominated"}. ${selected.is_in_cache_after ? "Present in cache after event." : "Not in cache after event."}${selected.dominated_by.length ? ` Dominated by ${selectedDominators.map((point) => point.query).join("; ")}.` : ""}`
                    : selected.is_frontier
                      ? `Non-dominated in this replay snapshot; ${selected.is_in_cache_after ? "retained" : "not retained"} after event.`
                      : `Dominated by ${selectedDominators.map((point) => point.query).join("; ") || "another equal-vector entry"}.`}
                </p>
              )}
            </div>
            {selected && (
              <dl className="plot-values">
                <div><dt>Token-saving proxy</dt><dd>{selected.token_saving_proxy}</dd></div>
                <div><dt>Volatility</dt><dd>{selected.volatility.toFixed(2)}</dd></div>
                <div><dt>Pareto status</dt><dd>{selected.is_frontier ? "Frontier" : "Dominated"}</dd></div>
              </dl>
            )}
          </div>

          <div className="plot-entry-list" aria-label="Accessible cache point selector">
            {points.map((point) => (
              <button
                type="button"
                key={`select-${point.id}`}
                className={selected?.id === point.id ? "plot-entry is-selected" : "plot-entry"}
                onClick={() => setSelectedId(point.id)}
              >
                <span className={`entry-marker ${point.is_candidate ? "candidate" : point.is_frontier ? "frontier" : "dominated"}`} aria-hidden="true" />
                <span>{point.query}</span>
                <small>
                  {point.token_saving_proxy} tokens · risk {point.volatility.toFixed(2)}
                </small>
              </button>
            ))}
          </div>
        </>
      )}
      <p className="method-note">
        Values are computed from the selected dataset replay. Token saving is
        the backend proxy (query + answer token count); volatility is the
        backend keyword-classifier score, not measured answer freshness.
      </p>
    </div>
  );
}
