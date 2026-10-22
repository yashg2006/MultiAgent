import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";

import { mergeStep, useTaskStream } from "../hooks/useTaskStream";
import type { RunStep, Task } from "../types";

class FakeEventSource {
  static CLOSED = 2;
  static instances: FakeEventSource[] = [];
  readyState = 0;
  closed = false;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private listeners: Record<string, ((e: MessageEvent<string>) => void)[]> = {};

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, fn: (e: MessageEvent<string>) => void) {
    (this.listeners[type] ??= []).push(fn);
  }

  emit(type: string, data: unknown) {
    for (const fn of this.listeners[type] ?? []) {
      fn(new MessageEvent(type, { data: JSON.stringify(data) }));
    }
  }

  close() {
    this.closed = true;
    this.readyState = FakeEventSource.CLOSED;
  }
}

const step = (seq: number, step_name = "research"): RunStep => ({
  seq,
  step_name,
  status: "success",
  latency_seconds: 0.1,
  detail: null,
});

const task: Task = {
  id: "t1",
  input_task: "goal",
  status: "running",
  result: null,
  error: null,
  retries_used: null,
  steps: [step(1, "planner")],
  created_at: "2026-10-21T14:00:00",
  updated_at: "2026-10-21T14:00:00",
};

function setup(enabled = true) {
  const client = new QueryClient();
  client.setQueryData(["task", "t1"], task);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const hook = renderHook(({ on }) => useTaskStream("t1", on), {
    wrapper,
    initialProps: { on: enabled },
  });
  return { client, hook };
}

describe("mergeStep", () => {
  it("appends new steps and ignores ones already present", () => {
    expect(mergeStep(task, step(2)).steps).toHaveLength(2);
    expect(mergeStep(task, step(1, "planner"))).toBe(task);
  });
});

describe("useTaskStream", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("opens the run's event stream and merges steps into the cache", () => {
    const { client, hook } = setup();
    const source = FakeEventSource.instances[0];
    expect(source.url).toBe("/tasks/t1/events");
    act(() => source.onopen?.());
    expect(hook.result.current).toBe("live");
    act(() => {
      source.emit("step", step(1, "planner")); // replayed duplicate
      source.emit("step", step(2));
    });
    expect(client.getQueryData<Task>(["task", "t1"])?.steps?.map((s) => s.seq)).toEqual([1, 2]);
  });

  it("applies status changes, then the final task on done, and closes", () => {
    const { client, hook } = setup();
    const source = FakeEventSource.instances[0];
    act(() => source.emit("status", { status: "running", cancel_requested: true }));
    expect(client.getQueryData<Task>(["task", "t1"])?.cancel_requested).toBe(true);
    act(() => source.emit("done", { ...task, status: "success" }));
    expect(client.getQueryData<Task>(["task", "t1"])?.status).toBe("success");
    expect(source.closed).toBe(true);
    expect(hook.result.current).toBe("closed");
  });

  it("waits for done before applying a finished status, so the result isn't lost", () => {
    const { client } = setup();
    const source = FakeEventSource.instances[0];
    // The server sends the finished status first, then done with the full task.
    act(() => source.emit("status", { status: "success", cancel_requested: false }));
    expect(client.getQueryData<Task>(["task", "t1"])?.status).toBe("running");
    act(() =>
      source.emit("done", { ...task, status: "success", result: { "st-1": { findings: "x" } } }),
    );
    const updated = client.getQueryData<Task>(["task", "t1"]);
    expect(updated?.status).toBe("success");
    expect(updated?.result).toEqual({ "st-1": { findings: "x" } });
  });

  it("reports reconnecting on a transient error", () => {
    const { hook } = setup();
    act(() => FakeEventSource.instances[0].onerror?.());
    expect(hook.result.current).toBe("reconnecting");
  });

  it("closes the stream when disabled or unmounted, and doesn't open when disabled", () => {
    const { hook } = setup();
    const source = FakeEventSource.instances[0];
    hook.rerender({ on: false });
    expect(source.closed).toBe(true);
    expect(FakeEventSource.instances).toHaveLength(1);
    hook.unmount();
  });
});
