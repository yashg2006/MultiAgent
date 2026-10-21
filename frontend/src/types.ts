/** Mirrors `TaskOut` in src/api/schemas.py. */
export type TaskStatus = "pending" | "success" | "partial" | "error" | "cancelled";

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
  steps: RunStep[] | null;
  usage?: Usage | null;
  created_at: string;
  updated_at: string;
}
