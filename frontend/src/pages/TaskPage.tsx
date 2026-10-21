import { useParams } from "react-router-dom";

import { RunTrace } from "../components/RunTrace";
import { StatusBadge } from "../components/StatusBadge";
import { useTask } from "../hooks/useTasks";
import { taskToMarkdown } from "../markdown";
import { formatApiTime } from "../time";
import type { Task } from "../types";

function downloadMarkdown(task: Task) {
  const blob = new Blob([taskToMarkdown(task)], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `run-${task.id.slice(0, 8)}.md`;
  link.click();
  URL.revokeObjectURL(url);
}

const PROBLEM_HEADING: Record<string, string> = {
  partial: "Validation didn't pass",
  error: "The run failed",
};

export function TaskPage() {
  const { id = "" } = useParams();
  const { data: task, isPending, isError, error } = useTask(id);

  if (isPending) return <p className="text-sm text-steel">Loading run…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-fail">
        Couldn't load this run: {error.message}
      </p>
    );
  }

  const findings = Object.entries(task.result ?? {});
  const finished = task.status !== "pending";

  return (
    <article className="space-y-8">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={task.status} />
          <span className="text-xs text-steel">Started {formatApiTime(task.created_at)}</span>
          <span className="text-xs text-steel">
            Run <span className="font-mono">{task.id.slice(0, 8)}</span>
          </span>
        </div>
        <h2 className="max-w-[60ch] text-2xl font-semibold leading-snug text-ink">
          {task.input_task}
        </h2>
        {finished && (
          <button
            type="button"
            onClick={() => downloadMarkdown(task)}
            className="text-sm font-medium text-action underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-action"
          >
            Download as Markdown
          </button>
        )}
      </header>

      {task.error && (
        <section className="rounded-md border border-fail/30 bg-white p-4">
          <h3 className="text-sm font-medium text-fail">
            {PROBLEM_HEADING[task.status] ?? "Problem"}
          </h3>
          <p className="mt-1 text-sm text-ink">{task.error}</p>
        </section>
      )}

      <section>
        <h3 className="mb-3 text-base font-semibold text-ink">How the agents ran</h3>
        {task.status === "pending" ? (
          <p className="text-sm text-steel">
            The planner, research, and validator agents are working. This page updates on its own.
          </p>
        ) : (
          <RunTrace steps={task.steps ?? []} />
        )}
      </section>

      {findings.length > 0 && (
        <section>
          <h3 className="mb-3 text-base font-semibold text-ink">Findings</h3>
          <ul className="divide-y divide-rule border-y border-rule">
            {findings.map(([subTaskId, sub]) => (
              <li key={subTaskId} className="py-4">
                <p className="text-sm font-medium text-ink">{sub.query ?? subTaskId}</p>
                <p
                  className={`mt-1 max-w-[72ch] text-sm leading-relaxed ${sub.error ? "text-fail" : "text-steel"}`}
                >
                  {sub.error ? `Failed: ${sub.error}` : sub.findings}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
