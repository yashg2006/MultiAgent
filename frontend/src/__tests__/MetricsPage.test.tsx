import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";

import { MetricsPage } from "../pages/MetricsPage";
import type { Stats } from "../types";

function renderWith(stats: Stats) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(stats), { status: 200 }),
  );
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MetricsPage />
    </QueryClientProvider>,
  );
}

const zeroUsage = { calls: 0, retries: 0, input_tokens: 0, output_tokens: 0, cost_usd: 0 };

describe("MetricsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("invites the user to run a task when there are no runs", async () => {
    renderWith({ total_runs: 0, by_status: {}, success_rate: null, usage: zeroUsage });
    expect(await screen.findByText(/No runs yet/)).toBeInTheDocument();
  });

  it("shows totals, success rate and outcome counts", async () => {
    renderWith({
      total_runs: 5,
      by_status: { success: 3, partial: 1, error: 1 },
      success_rate: 0.6,
      usage: { ...zeroUsage, calls: 25 },
    });
    expect(await screen.findByText("5")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Passed")).toBeInTheDocument());
  });
});
