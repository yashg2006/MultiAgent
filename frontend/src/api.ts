import type { Stats, Task, User } from "./types";

const API_URL: string = import.meta.env.VITE_API_URL ?? "";

/** An HTTP error from the API, with its status code. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

/** Turn FastAPI's error body (a string, or a list of validation errors) into one sentence. */
function errorMessage(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (typeof first.msg === "string") return first.msg.replace(/^Value error, /, "");
  }
  return `Request failed with status ${status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // The session is an httpOnly cookie; "include" also sends it when the API is
  // on another origin (VITE_API_URL).
  const response = await fetch(`${API_URL}${path}`, { credentials: "include", ...init });
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = ((await response.json()) as { detail?: unknown }).detail;
    } catch {
      // Body wasn't JSON; fall back to the status code.
    }
    throw new ApiError(errorMessage(detail, response.status), response.status);
  }
  if (response.status === 204) return undefined as T;
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

export function getStats(): Promise<Stats> {
  return request<Stats>("/tasks/stats/summary");
}

export function cancelTask(id: string): Promise<Task> {
  return request<Task>(`/tasks/${encodeURIComponent(id)}/cancel`, { method: "POST" });
}

/** URL of a run's live step stream (Server-Sent Events). */
export function taskEventsUrl(id: string): string {
  return `${API_URL}/tasks/${encodeURIComponent(id)}/events`;
}

/** The signed-in user, or null when signed out. */
export async function getMe(): Promise<User | null> {
  try {
    return await request<User>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

function sendCredentials(path: string, email: string, password: string): Promise<User> {
  return request<User>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export const signIn = (email: string, password: string) =>
  sendCredentials("/auth/login", email, password);

export const register = (email: string, password: string) =>
  sendCredentials("/auth/register", email, password);

export function signOut(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}
