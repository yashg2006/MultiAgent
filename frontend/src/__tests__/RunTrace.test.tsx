import { render, screen } from "@testing-library/react";

import { groupSteps, RunTrace } from "../components/RunTrace";
import type { RunStep } from "../types";

const step = (step_name: string, status = "success", latency_seconds = 0.01): RunStep => ({
  step_name,
  status,
  latency_seconds,
  detail: null,
});

// Shape produced by Orchestrator.run() when the first validation is rejected
// and the retry passes: planner, then (research x2 -> validator) twice.
const retriedRun: RunStep[] = [
  step("planner"),
  step("research"),
  step("research"),
  step("validator", "rejected"),
  step("research"),
  step("research"),
  step("validator", "success"),
];

describe("groupSteps", () => {
  it("separates the planner and groups each research->validator cycle as an attempt", () => {
    const { planner, attempts } = groupSteps(retriedRun);
    expect(planner).toHaveLength(1);
    expect(attempts).toHaveLength(2);
    expect(attempts[0].steps).toHaveLength(2);
    expect(attempts[0].verdict?.status).toBe("rejected");
    expect(attempts[1].verdict?.status).toBe("success");
  });

  it("keeps trailing research steps with no validator as an open attempt", () => {
    const { attempts } = groupSteps([step("planner"), step("research")]);
    expect(attempts).toEqual([{ steps: [step("research")], verdict: null }]);
  });

  it("handles a planner-only run (planner failed)", () => {
    const { planner, attempts } = groupSteps([step("planner", "error")]);
    expect(planner).toHaveLength(1);
    expect(attempts).toHaveLength(0);
  });
});

describe("RunTrace", () => {
  it("labels a rejected attempt that was retried, and the final one that was not", () => {
    const exhausted = [...retriedRun.slice(0, 6), step("validator", "rejected")];
    render(<RunTrace steps={exhausted} />);
    expect(screen.getByText("rejected by validator, retried")).toBeInTheDocument();
    expect(screen.getByText("rejected by validator, no retries left")).toBeInTheDocument();
  });

  it("shows latency in milliseconds", () => {
    render(<RunTrace steps={[step("planner", "success", 0.0123)]} />);
    expect(screen.getByText("12.3 ms")).toBeInTheDocument();
  });

  it("shows a step's error detail", () => {
    render(
      <RunTrace
        steps={[{ ...step("planner", "error"), detail: { error: "simulated agent crash" } }]}
      />,
    );
    expect(screen.getByText("simulated agent crash")).toBeInTheDocument();
  });

  it("explains an empty finished run, and renders nothing while live", () => {
    render(<RunTrace steps={[]} />);
    expect(screen.getByText("This run recorded no steps.")).toBeInTheDocument();
    const { container } = render(<RunTrace steps={[]} live />);
    expect(container).toBeEmptyDOMElement();
  });

  it("doesn't claim retries are exhausted while the run is still going", () => {
    render(<RunTrace steps={retriedRun.slice(0, 4)} live />);
    expect(screen.getByText("rejected by validator")).toBeInTheDocument();
    expect(screen.queryByText(/no retries left/)).not.toBeInTheDocument();
  });
});
