import { useQuery } from "@tanstack/react-query";

import { getStats } from "../api";
import { describeUsage } from "../usage";

const STATUS_LABELS: Record<string, string> = {
  success: "Passed",
  partial: "Partial",
  error: "Failed",
  cancelled: "Cancelled",
  running: "Running",
  pending: "Queued",
};

const STATUS_BAR: Record<string, string> = {
  success: "bg-ok",
  partial: "bg-warn",
  error: "bg-fail",
  cancelled: "bg-faint",
  running: "bg-accent",
  pending: "bg-line-strong",
};

function Stat({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div className={`card p-5 ${emphasis ? "ring-1 ring-accent/15" : ""}`}>
      <p
        className={`font-display font-semibold tracking-tight text-ink ${
          emphasis ? "text-4xl text-accent-hover" : "text-3xl"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-sm text-muted">{label}</p>
    </div>
  );
}

export function MetricsPage() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  if (isPending) return <p className="text-sm text-muted">Loading your stats…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-fail">
        Couldn't load stats: {error.message}
      </p>
    );
  }
  if (data.total_runs === 0) {
    return (
      <p className="rounded-lg border border-dashed border-line px-4 py-6 text-sm text-muted">
        No runs yet. Your stats appear once you run a task.
      </p>
    );
  }

  const successRate = data.success_rate === null ? "—" : `${Math.round(data.success_rate * 100)}%`;
  const usage = describeUsage(data.usage);
  const outcomes = Object.entries(data.by_status).sort((a, b) => b[1] - a[1]);
  const maxCount = Math.max(...outcomes.map(([, n]) => n), 1);

  return (
    <div className="space-y-8 motion-safe:animate-rise">
      <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">Your runs</h2>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Success rate" value={successRate} emphasis />
        <Stat label="Total runs" value={String(data.total_runs)} />
        <Stat label="Model calls" value={String(data.usage.calls)} />
      </div>

      <section className="space-y-3">
        <h3 className="font-display text-base font-semibold text-ink">By outcome</h3>
        <ul className="space-y-2.5">
          {outcomes.map(([status, count]) => (
            <li key={status} className="flex items-center gap-3 text-sm">
              <span className="w-20 shrink-0 text-ink">{STATUS_LABELS[status] ?? status}</span>
              <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-sunken" aria-hidden>
                <span
                  className={`absolute inset-y-0 left-0 rounded-full ${STATUS_BAR[status] ?? "bg-faint"}`}
                  style={{ width: `${Math.max(4, (count / maxCount) * 100)}%` }}
                />
              </span>
              <span className="tabular w-8 shrink-0 text-right font-mono text-xs text-muted">
                {count}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {usage.length > 0 && (
        <section className="space-y-2">
          <h3 className="font-display text-base font-semibold text-ink">Model usage</h3>
          <div className="flex flex-wrap gap-2">
            {usage.map((part) => (
              <span
                key={part}
                className="rounded-full border border-line bg-surface px-2.5 py-1 text-xs text-muted shadow-card"
              >
                {part}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
