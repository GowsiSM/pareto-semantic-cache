import { useCallback, useState } from "react";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { Section } from "./components/Section";
import { ArchitectureDiagram } from "./components/ArchitectureDiagram";
import { HowParetoWorks } from "./components/HowParetoWorks";
import { RunExperimentPanel } from "./components/RunExperimentPanel";
import { StatusBanner } from "./components/StatusBanner";
import { ResultsTable } from "./components/ResultsTable";
import { ResultsCharts } from "./components/ResultsCharts";
import { ConclusionSection } from "./components/ConclusionSection";
import { useExperiment } from "./hooks/useExperiment";
import { useTheme } from "./hooks/useTheme";

function App() {
  const experiment = useExperiment();
  const { theme, toggleTheme } = useTheme();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    architecture: true,
    "how-pareto-works": true,
    "run-experiment": true,
    results: true,
    conclusion: true,
  });

  const handleNavigate = useCallback((id: string) => {
    setExpanded((previous) => ({ ...previous, [id]: !previous[id] }));
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, []);

  return (
    <div className="app">
      <Nav theme={theme} onToggleTheme={toggleTheme} onNavigate={handleNavigate} />
      <Hero />

      <Section
        id="architecture"
        expanded={expanded.architecture}
        eyebrow="Architecture"
        title="SCALM vs. Pareto"
        description="Both extend the same semantic-cache pipeline (embed -> similarity search -> hit/miss). They differ only in how a cache-miss candidate is admitted and what gets evicted under capacity."
      >
        <ArchitectureDiagram />
      </Section>

      <Section
        id="how-pareto-works"
        expanded={expanded["how-pareto-works"]}
        eyebrow="Mechanism"
        title="How Pareto admission works"
        description="Two objectives, no fixed weight between them."
      >
        <HowParetoWorks />
      </Section>

      <Section
        id="run-experiment"
        expanded={expanded["run-experiment"]}
        eyebrow="Live demo"
        title="Run an experiment"
        description="This calls the backend API directly. See the README for the API contract the backend must implement."
      >
        <RunExperimentPanel onRun={experiment.run} isLoading={experiment.status === "loading"} />
      </Section>

      <Section
        id="results"
        expanded={expanded.results}
        eyebrow="Results"
        title="Measured comparison"
        description="Populated only from the backend's response to the most recent run."
      >
        <StatusBanner
          status={experiment.status}
          error={experiment.error}
          errorDetail={experiment.errorDetail}
        />
        {experiment.status === "success" && experiment.data && (
          <>
            <ResultsTable results={experiment.data.systems} />
            <ResultsCharts results={experiment.data.systems} theme={theme} />
            <div className="run-meta">
              {experiment.data.meta.embedding_model} - {experiment.data.meta.dataset_size}{" "}
              queries - {experiment.data.meta.duration_ms}ms
            </div>
          </>
        )}
      </Section>

      <Section
        id="conclusion"
        expanded={expanded.conclusion}
        eyebrow="Interpretation"
        title="Trade-offs, not a winner"
        description="Generated from the actual returned metrics each run."
      >
        {experiment.status === "success" && experiment.data ? (
          <ConclusionSection results={experiment.data.systems} />
        ) : (
          <p className="conclusion-placeholder">
            Run an experiment above to see a trade-off summary computed from
            its results.
          </p>
        )}
      </Section>

      <footer className="footer">
        SemantiCache -- final-year project. Results are produced by the
        connected backend, not simulated in this interface.
      </footer>
    </div>
  );
}

export default App;
