import type { Task } from "./types";
import { describeUsage } from "./usage";

/** Render a finished run as a Markdown document for download. */
export function taskToMarkdown(task: Task): string {
  const lines: string[] = [
    `# ${task.input_task}`,
    "",
    `- Status: ${task.status}`,
    `- Run ID: ${task.id}`,
    `- Started: ${task.created_at}`,
    `- Validation retries: ${task.retries_used ?? 0}`,
  ];
  const usage = describeUsage(task.usage);
  if (usage.length > 0) lines.push(`- Model usage: ${usage.join(", ")}`);

  if (task.error) {
    lines.push("", "## Problem", "", task.error);
  }

  const entries = Object.entries(task.result ?? {});
  if (entries.length > 0) {
    lines.push("", "## Findings");
    for (const [subTaskId, sub] of entries) {
      lines.push("", `### ${subTaskId}`, "");
      if (sub.query) lines.push(`Question: ${sub.query}`, "");
      lines.push(sub.error ? `Failed: ${sub.error}` : (sub.findings ?? "No findings returned."));
      for (const source of sub.sources ?? []) {
        lines.push("", `Source: [${source.title}](${source.url})`);
      }
    }
  }

  const steps = task.steps ?? [];
  if (steps.length > 0) {
    lines.push("", "## Steps", "", "| Agent | Status | Time (ms) |", "|---|---|---:|");
    for (const step of steps) {
      lines.push(
        `| ${step.step_name} | ${step.status} | ${(step.latency_seconds * 1000).toFixed(1)} |`,
      );
    }
  }

  return lines.join("\n") + "\n";
}
