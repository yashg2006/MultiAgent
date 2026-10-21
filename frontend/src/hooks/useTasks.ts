import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { cancelTask, createTask, getTask, listTasks } from "../api";
import { isActive, type Task } from "../types";

// The live stream (useTaskStream) delivers progress; polling is only a
// fallback in case the stream can't connect (e.g. a proxy that blocks it).
const FALLBACK_POLL_MS = 3000;

/** A single run; polls slowly while it's queued or running. */
export function useTask(id: string) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => getTask(id),
    refetchInterval: (query) =>
      query.state.data && isActive(query.state.data.status) ? FALLBACK_POLL_MS : false,
  });
}

/** Run history; refreshes while any run is still active. */
export function useTasks() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: listTasks,
    refetchInterval: (query) =>
      query.state.data?.some((t: Task) => isActive(t.status)) ? FALLBACK_POLL_MS : false,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createTask,
    onSuccess: (task) => {
      queryClient.setQueryData(["task", task.id], task);
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useCancelTask(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => cancelTask(id),
    onSuccess: (task) => {
      queryClient.setQueryData<Task>(["task", id], (old) =>
        old ? { ...old, cancel_requested: task.cancel_requested } : task,
      );
    },
  });
}
