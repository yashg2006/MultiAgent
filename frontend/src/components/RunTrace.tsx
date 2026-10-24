import type { RunStep } from "../types";

const AGENT_NAMES: Record<string, string> = {
  planner: "Planner",
  research: "Research",
  validator: "Validator",
};

/** Agent identity colour (the dot), distinct from the per-step status colour. */
const AGENT_DOT: Record<string, string> = {
  planner: "bg-[#6B63E8]",
  research: "bg-[#2FA882]",
  validator: "bg-[#D08A2E]",
};

const BAR_COLOR: Record<string, string> = {
  success: "bg-ok",
  rejected: "bg-warn",
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
  const widthPct = maxLatency > 0 ? Math.max(3, (step.latency_seconds / maxLatency) * 100) : 3;
  const error = typeof step.detail?.error === "string" ? step.detail.error : null;
  const settled = step.status in BAR_COLOR;
  const barColor = BAR_COLOR[step.status] ?? "bg-accent";
  return (
    <li className="group grid grid-cols-[7rem_1fr_4.75rem] items-center gap-3 py-[7px]">
      <span className="flex items-center gap-2 text-sm text-ink">
        <span
          aria-hidden
          className={`h-2 w-2 shrink-0 rounded-full ${AGENT_DOT[step.step_name] ?? "bg-faint"}`}
        />
        {AGENT_NAMES[step.step_name] ?? step.step_name}
      </span>
      <span className="relative h-2.5 overflow-hidden rounded-full bg-sunken" aria-hidden>
        <span
          className={`absolute inset-y-0 left-0 origin-left rounded-full ${barColor} ${
            settled ? "motion-safe:animate-fill-in" : "motion-safe:animate-pulse"
          }`}
          style={{ width: `${widthPct}%` }}
        />
      </span>
      <span className="tabular text-right font-mono text-xs text-muted">{ms.toFixed(1)} ms</span>
      <span className="sr-only">
        {step.step_name} {step.status}
      </span>
      {error && (
        <span className="col-span-3 -mt-0.5 rounded bg-fail-soft px-2 py-1 text-xs text-fail">
          {error}
        </span>
      )}
    </li>
  );
}

export function RunTrace({ steps, live = false }: { steps: RunStep[]; live?: boolean }) {
  if (steps.length === 0) {
    return live ? null : (
      <p className="rounded-lg border border-dashed border-line px-4 py-6 text-center text-sm text-muted">
        This run recorded no steps.
      </p>
    );
  }
  const maxLatency = Math.max(...steps.map((s) => s.latency_seconds));
  const { planner, attempts } = groupSteps(steps);

  return (
    <div className="card overflow-hidden">
      {planner.length > 0 && (
        <ol className="border-b border-line px-4 py-2">
          {planner.map((step, i) => (
            <StepRow key={`p${i}`} step={step} maxLatency={maxLatency} />
          ))}
        </ol>
      )}
      <div className="divide-y divide-line">
        {attempts.map((attempt, i) => {
          const rejected = attempt.verdict?.status === "rejected";
          return (
            <section key={i} aria-label={`Attempt ${i + 1}`} className="px-4 py-2.5">
              <div className="mb-1 flex items-center gap-2">
                <h4 className="font-display text-xs font-medium text-ink">Attempt {i + 1}</h4>
                {rejected && (
                  <span className="rounded-full bg-warn-soft px-2 py-0.5 text-2xs font-medium text-warn">
                    {i < attempts.length - 1
                      ? "rejected by validator, retried"
                      : live
                        ? "rejected by validator"
                        : "rejected by validator, no retries left"}
                  </span>
                )}
              </div>
              <ol>
                {attempt.steps.map((step, j) => (
                  <StepRow key={j} step={step} maxLatency={maxLatency} />
                ))}
                {attempt.verdict && <StepRow step={attempt.verdict} maxLatency={maxLatency} />}
              </ol>
            </section>
          );
        })}
      </div>
    </div>
  );
}
