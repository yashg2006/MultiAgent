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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-rule bg-white p-4">
      <p className="text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-steel">{label}</p>
    </div>
  );
}

export function MetricsPage() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  if (isPending) return <p className="text-sm text-steel">Loading your stats…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-fail">
        Couldn't load stats: {error.message}
      </p>
    );
  }
  if (data.total_runs === 0) {
    return (
      <p className="text-sm text-steel">No runs yet. Your stats appear once you run a task.</p>
    );
  }

  const successRate = data.success_rate === null ? "—" : `${Math.round(data.success_rate * 100)}%`;
  const usage = describeUsage(data.usage);

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-semibold text-ink">Your runs</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Total runs" value={String(data.total_runs)} />
        <Stat label="Success rate" value={successRate} />
        <Stat label="Model calls" value={String(data.usage.calls)} />
      </div>

      <section>
        <h3 className="mb-3 text-base font-semibold text-ink">By outcome</h3>
        <ul className="divide-y divide-rule border-y border-rule">
          {Object.entries(data.by_status)
            .sort((a, b) => b[1] - a[1])
            .map(([status, count]) => (
              <li key={status} className="flex items-center justify-between py-2 text-sm">
                <span className="text-ink">{STATUS_LABELS[status] ?? status}</span>
                <span className="font-mono text-steel">{count}</span>
              </li>
            ))}
        </ul>
      </section>

      {usage.length > 0 && (
        <section>
          <h3 className="mb-2 text-base font-semibold text-ink">Model usage</h3>
          <p className="text-sm text-steel">{usage.join(" · ")}</p>
        </section>
      )}
    </div>
  );
}
