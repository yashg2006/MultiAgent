import { useState, type FormEvent, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useCreateTask } from "../hooks/useTasks";

export function TaskComposer() {
  const [text, setText] = useState("");
  const navigate = useNavigate();
  const createTask = useCreateTask();
  const canSubmit = text.trim().length > 0 && !createTask.isPending;

  function submit() {
    if (!canSubmit) return;
    createTask.mutate(text.trim(), {
      onSuccess: (task) => {
        setText("");
        navigate(`/runs/${task.id}`);
      },
    });
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2.5">
      <label htmlFor="task" className="block font-display text-sm font-medium text-ink">
        What should the agents work on?
      </label>
      <div className="group rounded-lg border border-line bg-surface shadow-card transition-colors focus-within:border-accent/60 focus-within:shadow-glow">
        <textarea
          id="task"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={4}
          placeholder="Compare rate-monotonic and EDF scheduling for a small embedded system"
          className="block w-full resize-y rounded-t-lg bg-transparent px-3.5 py-3 text-sm leading-relaxed text-ink placeholder:text-faint focus:outline-none"
        />
        <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-2">
          <span className="text-2xs text-faint">
            <kbd className="font-sans">Ctrl</kbd> + <kbd className="font-sans">Enter</kbd> to run
          </span>
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-3.5 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-45"
          >
            {createTask.isPending ? (
              <>
                <Spinner /> Starting…
              </>
            ) : (
              "Run task"
            )}
          </button>
        </div>
      </div>
      {createTask.isError && (
        <div role="alert" className="rounded-md bg-fail-soft px-3 py-2 text-xs text-fail">
          <p className="font-medium">Couldn't start the run ({createTask.error.message}).</p>
          <p className="mt-0.5 text-fail/80">Check that the API server is running, then try again.</p>
        </div>
      )}
    </form>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="h-3 w-3 rounded-full border-[1.5px] border-white/40 border-t-white motion-safe:animate-spin"
    />
  );
}
