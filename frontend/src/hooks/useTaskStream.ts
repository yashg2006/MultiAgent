import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { taskEventsUrl } from "../api";
import type { RunStep, Task } from "../types";

export type StreamState = "connecting" | "live" | "reconnecting" | "closed";

/** Add a streamed step to a cached task, ignoring duplicates (by seq). */
export function mergeStep(task: Task, step: RunStep): Task {
  const steps = task.steps ?? [];
  if (step.seq !== undefined && steps.some((s) => s.seq === step.seq)) return task;
  return { ...task, steps: [...steps, step] };
}

/**
 * Follows a run's live step stream while `enabled`, writing each step into the
 * React Query cache for ["task", id]. EventSource reconnects on its own and
 * resumes after the last step it saw (Last-Event-ID); the stream is closed on
 * "done", when disabled, and on unmount.
 */
export function useTaskStream(id: string, enabled: boolean): StreamState {
  const queryClient = useQueryClient();
  const [state, setState] = useState<StreamState>("closed");

  useEffect(() => {
    if (!enabled || typeof EventSource === "undefined") {
      setState("closed");
      return;
    }
    const source = new EventSource(taskEventsUrl(id), { withCredentials: true });
    setState("connecting");

    const update = (fn: (task: Task) => Task) =>
      queryClient.setQueryData<Task>(["task", id], (old) => (old ? fn(old) : old));

    const onStep = (event: MessageEvent<string>) => {
      const step = JSON.parse(event.data) as RunStep;
      update((task) => mergeStep(task, step));
    };
    const onStatus = (event: MessageEvent<string>) => {
      const { status, cancel_requested } = JSON.parse(event.data) as Pick<
        Task,
        "status" | "cancel_requested"
      >;
      update((task) => ({ ...task, status, cancel_requested }));
    };
    const onDone = (event: MessageEvent<string>) => {
      queryClient.setQueryData<Task>(["task", id], JSON.parse(event.data) as Task);
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      source.close();
      setState("closed");
    };

    source.addEventListener("step", onStep as EventListener);
    source.addEventListener("status", onStatus as EventListener);
    source.addEventListener("done", onDone as EventListener);
    source.onopen = () => setState("live");
    source.onerror = () =>
      setState(source.readyState === EventSource.CLOSED ? "closed" : "reconnecting");

    return () => {
      source.close();
    };
  }, [id, enabled, queryClient]);

  return state;
}
