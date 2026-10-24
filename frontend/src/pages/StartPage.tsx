const STAGES = [
  {
    name: "Planner",
    job: "breaks your goal into smaller questions",
    dot: "bg-[#6B63E8]",
  },
  {
    name: "Research",
    job: "answers each question, in parallel where it can",
    dot: "bg-[#2FA882]",
  },
  {
    name: "Validator",
    job: "checks the answers and sends them back for another pass if they fall short",
    dot: "bg-[#D08A2E]",
  },
] as const;

/** Shown in the main pane when no run is selected. */
export function StartPage() {
  return (
    <div className="max-w-[58ch] space-y-10 motion-safe:animate-rise">
      <div className="space-y-3">
        <p className="font-mono text-xs text-muted">Orchestrator · Planner · Research · Validator</p>
        <h2 className="font-display text-3xl font-semibold leading-[1.15] tracking-tight text-ink">
          Give the agents a goal and watch them split up the work.
        </h2>
        <p className="max-w-[48ch] text-sm leading-relaxed text-muted">
          One orchestrator coordinates three specialised agents to turn a task into a verified
          result. Write a goal on the left to start — each run's live trace and findings appear
          here.
        </p>
      </div>

      <ol className="relative space-y-6 border-l border-line pl-6">
        {STAGES.map((stage) => (
          <li key={stage.name} className="relative">
            <span
              aria-hidden
              className={`absolute -left-[1.6rem] top-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-canvas ${stage.dot}`}
            />
            <p className="font-display text-sm font-medium text-ink">{stage.name}</p>
            <p className="mt-0.5 text-sm leading-relaxed text-muted">{stage.job}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
