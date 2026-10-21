import type { Usage } from "./types";

/** Short, plain-language parts describing a run's model usage. */
export function describeUsage(usage: Usage | null | undefined): string[] {
  if (!usage || usage.calls === 0) return [];
  const parts = [`${usage.calls} model ${usage.calls === 1 ? "call" : "calls"}`];
  if (usage.retries > 0) {
    parts.push(`${usage.retries} ${usage.retries === 1 ? "retry" : "retries"}`);
  }
  const tokens = usage.input_tokens + usage.output_tokens;
  if (tokens > 0) {
    parts.push(`${tokens.toLocaleString("en-US")} tokens`);
    parts.push(usage.cost_usd < 0.01 ? "under $0.01" : `$${usage.cost_usd.toFixed(2)}`);
  }
  return parts;
}
