import { NavLink } from "react-router-dom";

import { useTasks } from "../hooks/useTasks";
import { formatApiTime } from "../time";
import { StatusBadge } from "./StatusBadge";

export function TaskHistory() {
  const { data, isPending, isError, error } = useTasks();

  if (isPending) return <p className="text-sm text-muted">Loading runs…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-fail">
        Couldn't load runs: {error.message}
      </p>
    );
  }
  if (data.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-line px-3 py-5 text-sm text-muted">
        No runs yet. Your first one will show up here.
      </p>
    );
  }

  return (
    <ul className="space-y-1">
      {data.map((task) => (
        <li key={task.id}>
          <NavLink
            to={`/runs/${task.id}`}
            className={({ isActive }) =>
              `block rounded-lg border px-3 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring ${
                isActive
                  ? "border-accent/30 bg-accent-soft/60 shadow-card"
                  : "border-transparent hover:border-line hover:bg-surface"
              }`
            }
          >
            <span className="line-clamp-2 text-sm leading-snug text-ink">{task.input_task}</span>
            <span className="mt-2 flex items-center justify-between gap-2">
              <span className="text-2xs text-faint">{formatApiTime(task.created_at)}</span>
              <StatusBadge status={task.status} />
            </span>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}
