import { createTask, getTask } from "../api";
import { taskToMarkdown } from "../markdown";
import { parseApiTime } from "../time";
import type { Task } from "../types";

const task: Task = {
  id: "abcdef12-0000-0000-0000-000000000000",
  input_task: "Compare EDF and RMS",
  status: "partial",
  result: {
    "st-1": { query: "What is EDF?", findings: "Earliest deadline first." },
    "st-2": { error: "research failed" },
  },
  error: "Validation failed after 3 attempt(s): 'st-2' contains an error",
  retries_used: 3,
  steps: [{ step_name: "planner", status: "success", latency_seconds: 0.0042, detail: null }],
  created_at: "2026-10-21T14:00:00",
  updated_at: "2026-10-21T14:00:01",
};

describe("parseApiTime", () => {
  it("treats zone-less API timestamps as UTC", () => {
    expect(parseApiTime("2026-10-21T14:00:00").toISOString()).toBe("2026-10-21T14:00:00.000Z");
  });

  it("respects an explicit offset", () => {
    expect(parseApiTime("2026-10-21T19:30:00+05:30").toISOString()).toBe(
      "2026-10-21T14:00:00.000Z",
    );
  });
});

describe("taskToMarkdown", () => {
  const md = taskToMarkdown(task);

  it("includes the goal, status, problem, and findings", () => {
    expect(md).toContain("# Compare EDF and RMS");
    expect(md).toContain("- Status: partial");
    expect(md).toContain("## Problem");
    expect(md).toContain("Question: What is EDF?");
    expect(md).toContain("Earliest deadline first.");
    expect(md).toContain("Failed: research failed");
  });

  it("renders the step table with latency in ms", () => {
    expect(md).toContain("| planner | success | 4.2 |");
  });
});

describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("POSTs the task text as JSON", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(task), { status: 201 }));
    await createTask("Compare EDF and RMS");
    expect(fetchMock).toHaveBeenCalledWith("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: "Compare EDF and RMS" }),
    });
  });

  it("surfaces the API's error detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Task 'x' not found." }), { status: 404 }),
    );
    await expect(getTask("x")).rejects.toThrow("Task 'x' not found.");
  });

  it("falls back to the status code when the error body isn't JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("oops", { status: 500 }));
    await expect(getTask("x")).rejects.toThrow("Request failed with status 500.");
  });
});
