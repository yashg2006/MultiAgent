import type { Task } from "./types";

const API_URL: string = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Body wasn't JSON; keep the status-based message.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function createTask(task: string): Promise<Task> {
  return request<Task>("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task }),
  });
}

export function listTasks(): Promise<Task[]> {
  return request<Task[]>("/tasks");
}

export function getTask(id: string): Promise<Task> {
  return request<Task>(`/tasks/${encodeURIComponent(id)}`);
}

export function cancelTask(id: string): Promise<Task> {
  return request<Task>(`/tasks/${encodeURIComponent(id)}/cancel`, { method: "POST" });
}

/** URL of a run's live step stream (Server-Sent Events). */
export function taskEventsUrl(id: string): string {
  return `${API_URL}/tasks/${encodeURIComponent(id)}/events`;
}
