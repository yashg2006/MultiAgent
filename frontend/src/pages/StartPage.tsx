const STAGES = [
  ["Planner", "breaks your goal into smaller questions"],
  ["Research", "answers each question"],
  ["Validator", "checks the answers and sends them back for another pass if they fall short"],
] as const;

/** Shown in the main pane when no run is selected. */
export function StartPage() {
  return (
    <div className="max-w-[56ch] space-y-6">
      <h2 className="text-2xl font-semibold leading-snug text-ink">
        Give the agents a goal and watch how they split up the work.
      </h2>
      <ol className="space-y-3">
        {STAGES.map(([name, job], i) => (
          <li key={name} className="flex gap-3 text-sm">
            <span className="w-5 shrink-0 text-steel">{i + 1}.</span>
            <span className="text-steel">
              <span className="font-medium text-ink">{name}</span> {job}
            </span>
          </li>
        ))}
      </ol>
      <p className="text-sm text-steel">
        Write a goal on the left to start. Each run's step trace and findings show up here.
      </p>
    </div>
  );
}
