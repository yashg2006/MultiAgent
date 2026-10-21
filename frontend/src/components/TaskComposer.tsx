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
    <form onSubmit={onSubmit} className="space-y-3">
      <label htmlFor="task" className="block text-sm font-medium text-ink">
        What should the agents work on?
      </label>
      <textarea
        id="task"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        rows={4}
        placeholder="Compare rate-monotonic and EDF scheduling for a small embedded system"
        className="w-full resize-y rounded-md border border-rule bg-white px-3 py-2 text-sm text-ink placeholder:text-steel/70 focus:border-action focus:outline-none focus:ring-2 focus:ring-action/30"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-steel">Ctrl + Enter to run</span>
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white hover:bg-action-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createTask.isPending ? "Starting…" : "Run task"}
        </button>
      </div>
      {createTask.isError && (
        <div role="alert" className="space-y-1 text-sm text-fail">
          <p>Couldn't start the run ({createTask.error.message}).</p>
          <p>Check that the API server is running, then try again.</p>
        </div>
      )}
    </form>
  );
}
