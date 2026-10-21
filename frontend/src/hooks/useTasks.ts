import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createTask, getTask, listTasks } from "../api";
import type { Task } from "../types";

const POLL_MS = 1000;

/** A single run; polls once a second while the pipeline is still running. */
export function useTask(id: string) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => getTask(id),
    refetchInterval: (query) => (query.state.data?.status === "pending" ? POLL_MS : false),
  });
}

/** Run history; keeps polling only while some run is still pending. */
export function useTasks() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: listTasks,
    refetchInterval: (query) =>
      query.state.data?.some((t: Task) => t.status === "pending") ? POLL_MS : false,
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
