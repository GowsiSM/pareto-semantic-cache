import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConclusionSection } from "../components/ConclusionSection";
import type { ExperimentResults } from "../api/types";

function makeResults(overrides: Partial<ExperimentResults>): ExperimentResults {
  const base = {
    hit_rate: 0.2,
    token_saving_rate: 0.2,
    staleness_rate: 0.02,
    false_hit_rate: 0.0,
    hits: 100,
    misses: 400,
    total_queries: 500,
  };
  return {
    gptcache: { ...base },
    scalm: { ...base },
    pareto: { ...base },
    ...overrides,
  };
}

describe("ConclusionSection", () => {
  it("correctly attributes the hit-rate win to whichever system actually has the highest value", () => {
    const results = makeResults({
      gptcache: {
        hit_rate: 0.9,
        token_saving_rate: 0.2,
        staleness_rate: 0.02,
        false_hit_rate: 0.0,
        hits: 450,
        misses: 50,
        total_queries: 500,
      },
    });

    render(<ConclusionSection results={results} />);

    const listItems = screen.getAllByRole("listitem");
    const hitRatioItem = listItems.find((li) => li.textContent?.includes("hit ratio"));
    expect(hitRatioItem?.textContent).toContain("GPTCache");
    expect(hitRatioItem?.textContent).toContain("90.0%");
  });

  it("attributes the staleness win to the LOWEST value, not the highest (lower is better)", () => {
    const results = makeResults({
      pareto: {
        hit_rate: 0.2,
        token_saving_rate: 0.2,
        staleness_rate: 0.001, // much lower than the 0.02 baseline
        false_hit_rate: 0.0,
        hits: 100,
        misses: 400,
        total_queries: 500,
      },
    });

    render(<ConclusionSection results={results} />);

    // Pareto should be credited for staleness specifically
    const listItems = screen.getAllByRole("listitem");
    const stalenessItem = listItems.find((li) => li.textContent?.includes("staleness"));
    expect(stalenessItem?.textContent).toContain("Pareto");
  });

  it("never renders a literal overall-winner declaration", () => {
    const results = makeResults({});
    render(<ConclusionSection results={results} />);

    expect(screen.queryByText(/overall winner/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/best system/i)).not.toBeInTheDocument();
  });

  it("changes its output when the underlying results change (proving it isn't a fixed narrative)", () => {
    const resultsA = makeResults({
      scalm: {
        hit_rate: 0.99,
        token_saving_rate: 0.2,
        staleness_rate: 0.02,
        false_hit_rate: 0.0,
        hits: 495,
        misses: 5,
        total_queries: 500,
      },
    });
    const { unmount } = render(<ConclusionSection results={resultsA} />);
    expect(screen.getByText(/99.0%/)).toBeInTheDocument();
    unmount();

    const resultsB = makeResults({});
    render(<ConclusionSection results={resultsB} />);
    expect(screen.queryByText(/99.0%/)).not.toBeInTheDocument();
  });
});
