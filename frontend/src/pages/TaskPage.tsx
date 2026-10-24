import { type ReactNode } from "react";
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

function Meta({ children }: { children: ReactNode }) {
  return <span className="text-xs text-muted">{children}</span>;
}

export function TaskPage() {
  const { id = "" } = useParams();
  const { data: task, isPending, isError, error } = useTask(id);
  const active = task !== undefined && isActive(task.status);
  const stream = useTaskStream(id, active);
  const cancel = useCancelTask(id);

  if (isPending) return <p className="text-sm text-muted">Loading run…</p>;
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
    <article className="space-y-8 motion-safe:animate-rise">
      <header className="space-y-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <StatusBadge status={task.status} />
          <Meta>Started {formatApiTime(task.created_at)}</Meta>
          <span aria-hidden className="h-1 w-1 rounded-full bg-line-strong" />
          <Meta>
            Run <span className="font-mono text-faint">{task.id.slice(0, 8)}</span>
          </Meta>
          {describeUsage(task.usage).map((part) => (
            <span key={part}>
              <span aria-hidden className="mr-3 inline-block h-1 w-1 rounded-full bg-line-strong align-middle" />
              <Meta>{part}</Meta>
            </span>
          ))}
        </div>

        <h2 className="max-w-[58ch] font-display text-[1.65rem] font-semibold leading-snug tracking-tight text-ink">
          {task.input_task}
        </h2>

        {active && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => cancel.mutate()}
              disabled={task.cancel_requested || cancel.isPending}
              className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm transition-colors hover:border-fail/50 hover:text-fail focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring disabled:cursor-not-allowed disabled:opacity-60"
            >
              {task.cancel_requested ? "Stopping…" : "Cancel run"}
            </button>
            {task.cancel_requested && (
              <span className="text-xs text-muted">
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
            className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-sm transition-colors hover:border-accent/50 hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
          >
            Download as Markdown
          </button>
        )}
      </header>

      {task.error && (
        <section className="rounded-lg border border-fail/25 bg-fail-soft/60 p-4">
          <h3 className="text-sm font-semibold text-fail">
            {PROBLEM_HEADING[task.status] ?? "Problem"}
          </h3>
          <p className="mt-1 text-sm text-ink">{task.error}</p>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h3 className="font-display text-base font-semibold text-ink">How the agents ran</h3>
          {active && (
            <span className="text-2xs text-faint" aria-live="polite">
              {task.status === "pending"
                ? "Queued"
                : stream === "reconnecting"
                  ? "Reconnecting…"
                  : "Live"}
            </span>
          )}
        </div>
        {active && (
          <p className="text-sm text-muted" aria-live="polite">
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
        <section className="space-y-3">
          <h3 className="font-display text-base font-semibold text-ink">Findings</h3>
          <ul className="space-y-3">
            {findings.map(([subTaskId, sub]) => (
              <li key={subTaskId} className="card p-4">
                <p className="text-sm font-medium text-ink">{sub.query ?? subTaskId}</p>
                <p
                  className={`mt-1.5 max-w-[72ch] whitespace-pre-line text-sm leading-relaxed ${
                    sub.error ? "text-fail" : "text-muted"
                  }`}
                >
                  {sub.error ? `Failed: ${sub.error}` : sub.findings}
                </p>
                {sub.sources && sub.sources.length > 0 && (
                  <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-line pt-3 text-xs text-faint">
                    <span>Sources</span>
                    {sub.sources.map((source) => (
                      <a
                        key={source.url}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-full bg-accent-soft px-2 py-0.5 font-medium text-accent-hover underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
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
