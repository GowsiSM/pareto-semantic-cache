function FlowBox({ label, muted = false }: { label: string; muted?: boolean }) {
  return <div className={`flow-box${muted ? " flow-box-muted" : ""}`}>{label}</div>;
}

function FlowArrow() {
  return (
    <div className="flow-arrow" aria-hidden="true">
      ↓
    </div>
  );
}

export function ArchitectureDiagram() {
  return (
    <div className="architecture-grid">
      <div className="flow-column">
        <div className="flow-column-title">SCALM</div>
        <FlowBox label="Query embedding" />
        <FlowArrow />
        <FlowBox label="Semantic cluster lookup" />
        <FlowArrow />
        <FlowBox label="Token-saving ratio (TSR) rank" />
        <FlowArrow />
        <FlowBox label="Admit only if MID / HIGH rank" muted />
        <FlowArrow />
        <FlowBox label="Single-score LFU eviction" muted />
      </div>

      <div className="flow-column">
        <div className="flow-column-title">Pareto</div>
        <FlowBox label="Query embedding" />
        <FlowArrow />
        <FlowBox label="Token-saving proxy + volatility score" />
        <FlowArrow />
        <FlowBox label="Pareto dominance check" />
        <FlowArrow />
        <FlowBox label="Admit only if non-dominated" muted />
        <FlowArrow />
        <FlowBox label="Hypervolume-contribution eviction" muted />
      </div>
    </div>
  );
}
