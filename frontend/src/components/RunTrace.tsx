import type { RunStep } from "../types";

const AGENT_NAMES: Record<string, string> = {
  planner: "Planner",
  research: "Research",
  validator: "Validator",
};

const BAR_COLOR: Record<string, string> = {
  success: "bg-ok",
  rejected: "bg-partial",
  error: "bg-fail",
};

interface Attempt {
  steps: RunStep[];
  verdict: RunStep | null;
}

/**
 * Split the flat step list from the orchestrator into the planning step and
 * one group per Research→Validator cycle, so retries are visible as attempts.
 */
export function groupSteps(steps: RunStep[]): { planner: RunStep[]; attempts: Attempt[] } {
  const planner = steps.filter((s) => s.step_name === "planner");
  const attempts: Attempt[] = [];
  let current: RunStep[] = [];
  for (const step of steps) {
    if (step.step_name === "planner") continue;
    if (step.step_name === "validator") {
      attempts.push({ steps: current, verdict: step });
      current = [];
    } else {
      current.push(step);
    }
  }
  if (current.length > 0) attempts.push({ steps: current, verdict: null });
  return { planner, attempts };
}

function StepRow({ step, maxLatency }: { step: RunStep; maxLatency: number }) {
  const ms = step.latency_seconds * 1000;
  const widthPct = maxLatency > 0 ? Math.max(2, (step.latency_seconds / maxLatency) * 100) : 2;
  const error = typeof step.detail?.error === "string" ? step.detail.error : null;
  return (
    <li className="grid grid-cols-[6.5rem_1fr_4.5rem] items-center gap-3 py-1.5 text-sm">
      <span className="text-ink">{AGENT_NAMES[step.step_name] ?? step.step_name}</span>
      <span className="relative h-2 rounded-sm bg-rule/60" aria-hidden>
        <span
          className={`absolute inset-y-0 left-0 rounded-sm motion-safe:transition-[width] motion-safe:duration-500 ${BAR_COLOR[step.status] ?? "bg-steel"}`}
          style={{ width: `${widthPct}%` }}
        />
      </span>
      <span className="text-right font-mono text-xs text-steel">{ms.toFixed(1)} ms</span>
      <span className="sr-only">
        {step.step_name} {step.status}
      </span>
      {error && <span className="col-span-3 -mt-1 text-xs text-fail">{error}</span>}
    </li>
  );
}

export function RunTrace({ steps }: { steps: RunStep[] }) {
  if (steps.length === 0) {
    return <p className="text-sm text-steel">The step trace appears when the run finishes.</p>;
  }
  const maxLatency = Math.max(...steps.map((s) => s.latency_seconds));
  const { planner, attempts } = groupSteps(steps);

  return (
    <div className="space-y-5">
      <ol>
        {planner.map((step, i) => (
          <StepRow key={`p${i}`} step={step} maxLatency={maxLatency} />
        ))}
      </ol>
      {attempts.map((attempt, i) => (
        <section key={i} aria-label={`Attempt ${i + 1}`} className="border-l-2 border-rule pl-4">
          <h4 className="mb-1 text-sm font-medium text-ink">
            Attempt {i + 1}
            {attempt.verdict?.status === "rejected" && (
              <span className="ml-2 font-normal text-partial">
                {i < attempts.length - 1
                  ? "rejected by validator, retried"
                  : "rejected by validator, no retries left"}
              </span>
            )}
          </h4>
          <ol>
            {attempt.steps.map((step, j) => (
              <StepRow key={j} step={step} maxLatency={maxLatency} />
            ))}
            {attempt.verdict && <StepRow step={attempt.verdict} maxLatency={maxLatency} />}
          </ol>
        </section>
      ))}
    </div>
  );
}
