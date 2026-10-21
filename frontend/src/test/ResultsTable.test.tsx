import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ResultsTable } from "../components/ResultsTable";
import type { ExperimentResults } from "../api/types";

const results: ExperimentResults = {
  gptcache: {
    hit_rate: 0.1,
    token_saving_rate: 0.1,
    staleness_rate: 0,
    false_hit_rate: 0,
    hits: 10,
    misses: 90,
    total_queries: 100,
  },
  scalm: {
    hit_rate: 0.2,
    token_saving_rate: 0.2,
    staleness_rate: 0.1,
    false_hit_rate: 0,
    hits: 20,
    misses: 80,
    total_queries: 100,
  },
  pareto: {
    hit_rate: 0.3,
    token_saving_rate: 0.3,
    staleness_rate: 0,
    false_hit_rate: 0,
    hits: 30,
    misses: 70,
    total_queries: 100,
  },
};

describe("ResultsTable", () => {
  it("keeps every metric row aligned with the selected system columns", () => {
    render(<ResultsTable results={results} systems={["scalm", "pareto"]} />);

    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(3);
    for (const row of within(table).getAllByRole("row").slice(1)) {
      expect(within(row).getAllByRole("cell")).toHaveLength(3);
    }
    expect(within(table).queryByText("10 / 90")).not.toBeInTheDocument();
    expect(within(table).getByText("20 / 80")).toBeInTheDocument();
    expect(within(table).getByText("30 / 70")).toBeInTheDocument();
  });
});
