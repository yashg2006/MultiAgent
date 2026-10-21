import { useParams } from "react-router-dom";

import { RunTrace } from "../components/RunTrace";
import { StatusBadge } from "../components/StatusBadge";
import { useCancelTask, useTask } from "../hooks/useTasks";
import { useTaskStream } from "../hooks/useTaskStream";
import { taskToMarkdown } from "../markdown";
import { formatApiTime } from "../time";
import { isActive, type Task } from "../types";
import { describeUsage } from "../usage";

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
  cancelled: "Run cancelled",
};

export function TaskPage() {
  const { id = "" } = useParams();
  const { data: task, isPending, isError, error } = useTask(id);
  const active = task !== undefined && isActive(task.status);
  const stream = useTaskStream(id, active);
  const cancel = useCancelTask(id);

  if (isPending) return <p className="text-sm text-steel">Loading run…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-fail">
        Couldn't load this run: {error.message}
      </p>
    );
  }

  const findings = Object.entries(task.result ?? {});
  const finished = !active;

  return (
    <article className="space-y-8">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={task.status} />
          <span className="text-xs text-steel">Started {formatApiTime(task.created_at)}</span>
          <span className="text-xs text-steel">
            Run <span className="font-mono">{task.id.slice(0, 8)}</span>
          </span>
          {describeUsage(task.usage).map((part) => (
            <span key={part} className="text-xs text-steel">
              {part}
            </span>
          ))}
        </div>
        <h2 className="max-w-[60ch] text-2xl font-semibold leading-snug text-ink">
          {task.input_task}
        </h2>
        {active && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => cancel.mutate()}
              disabled={task.cancel_requested || cancel.isPending}
              className="rounded-md border border-rule bg-white px-3 py-1.5 text-sm font-medium text-ink hover:border-fail hover:text-fail focus-visible:outline focus-visible:outline-2 focus-visible:outline-action disabled:cursor-not-allowed disabled:opacity-60"
            >
              {task.cancel_requested ? "Stopping…" : "Cancel run"}
            </button>
            {task.cancel_requested && (
              <span className="text-xs text-steel">
                The run stops after the step in progress; finished work is kept.
              </span>
            )}
            {cancel.isError && (
              <span role="alert" className="text-xs text-fail">
                Couldn't cancel: {cancel.error.message}
              </span>
            )}
          </div>
        )}
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
        {active && (
          <p className="mb-3 text-sm text-steel" aria-live="polite">
            {task.status === "pending"
              ? "Queued. The agents start as soon as a worker is free."
              : stream === "reconnecting"
                ? "Connection lost; reconnecting. Steps that finish meanwhile will still appear."
                : "The agents are working. Steps appear here as they finish."}
          </p>
        )}
        <RunTrace steps={task.steps ?? []} live={active} />
      </section>

      {findings.length > 0 && (
        <section>
          <h3 className="mb-3 text-base font-semibold text-ink">Findings</h3>
          <ul className="divide-y divide-rule border-y border-rule">
            {findings.map(([subTaskId, sub]) => (
              <li key={subTaskId} className="py-4">
                <p className="text-sm font-medium text-ink">{sub.query ?? subTaskId}</p>
                <p
                  className={`mt-1 max-w-[72ch] whitespace-pre-line text-sm leading-relaxed ${sub.error ? "text-fail" : "text-steel"}`}
                >
                  {sub.error ? `Failed: ${sub.error}` : sub.findings}
                </p>
                {sub.sources && sub.sources.length > 0 && (
                  <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-steel">
                    <span>Sources:</span>
                    {sub.sources.map((source) => (
                      <a
                        key={source.url}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-action underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-action"
                      >
                        {source.title}
                      </a>
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
