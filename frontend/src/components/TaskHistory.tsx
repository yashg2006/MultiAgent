import { NavLink } from "react-router-dom";

import { useTasks } from "../hooks/useTasks";
import { formatApiTime } from "../time";
import { StatusBadge } from "./StatusBadge";

export function TaskHistory() {
  const { data, isPending, isError, error } = useTasks();

  if (isPending) return <p className="text-sm text-steel">Loading runs…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-fail">
        Couldn't load runs: {error.message}
      </p>
    );
  }
  if (data.length === 0) {
    return <p className="text-sm text-steel">No runs yet. Your first one will show up here.</p>;
  }

  return (
    <ul className="divide-y divide-rule">
      {data.map((task) => (
        <li key={task.id}>
          <NavLink
            to={`/runs/${task.id}`}
            className={({ isActive }) =>
              `block px-2 py-3 -mx-2 rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-action ${
                isActive ? "bg-white" : "hover:bg-white/60"
              }`
            }
          >
            <span className="line-clamp-2 text-sm text-ink">{task.input_task}</span>
            <span className="mt-1.5 flex items-center justify-between gap-2">
              <span className="text-xs text-steel">{formatApiTime(task.created_at)}</span>
              <StatusBadge status={task.status} />
            </span>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}
