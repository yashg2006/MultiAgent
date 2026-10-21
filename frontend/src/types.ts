/** Mirrors `TaskOut` in src/api/schemas.py. */
export type TaskStatus = "pending" | "running" | "success" | "partial" | "error" | "cancelled";

/** Statuses after which a run never changes. */
export const FINISHED_STATUSES: ReadonlySet<string> = new Set([
  "success",
  "partial",
  "error",
  "cancelled",
]);

export function isActive(status: string): boolean {
  return !FINISHED_STATUSES.has(status);
}

/** Mirrors `LLMUsage` in src/shared/schemas.py. */
export interface Usage {
  calls: number;
  retries: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

/** Mirrors `RunStep` in src/shared/schemas.py. Agents report "rejected" too. */
export interface RunStep {
  /** Order in which the step finished, from 1. */
  seq?: number;
  step_name: string;
  status: string;
  latency_seconds: number;
  detail: Record<string, unknown> | null;
  sub_task_id?: string | null;
  usage?: Usage;
}

export interface Source {
  title: string;
  url: string;
}

export interface SubTaskResult {
  query?: string;
  findings?: string;
  error?: string;
  sources?: Source[];
}

export interface Task {
  id: string;
  input_task: string;
  status: TaskStatus;
  result: Record<string, SubTaskResult> | null;
  error: string | null;
  retries_used: number | null;
  cancel_requested?: boolean;
  steps: RunStep[] | null;
  usage?: Usage | null;
  created_at: string;
  updated_at: string;
}

/** Mirrors `UserOut` in src/api/auth.py. */
export interface User {
  id: string;
  email: string;
  created_at: string;
}

/** Mirrors the `/tasks/stats/summary` response in src/api/routes.py. */
export interface Stats {
  total_runs: number;
  by_status: Record<string, number>;
  success_rate: number | null;
  usage: Usage;
}
