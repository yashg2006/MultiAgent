/** Mirrors `TaskOut` in src/api/schemas.py. */
export type TaskStatus = "pending" | "success" | "partial" | "error";

/** Mirrors `RunStep` in src/shared/schemas.py. Agents report "rejected" too. */
export interface RunStep {
  step_name: string;
  status: string;
  latency_seconds: number;
  detail: Record<string, unknown> | null;
}

export interface SubTaskResult {
  query?: string;
  findings?: string;
  error?: string;
}

export interface Task {
  id: string;
  input_task: string;
  status: TaskStatus;
  result: Record<string, SubTaskResult> | null;
  error: string | null;
  retries_used: number | null;
  steps: RunStep[] | null;
  created_at: string;
  updated_at: string;
}
