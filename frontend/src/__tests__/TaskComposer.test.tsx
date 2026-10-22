import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TaskComposer } from "../components/TaskComposer";

function renderComposer() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<TaskComposer />} />
          <Route path="/runs/:id" element={<p>run page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TaskComposer", () => {
  afterEach(() => vi.restoreAllMocks());

  it("disables the run button until a goal is typed", () => {
    renderComposer();
    const button = screen.getByRole("button", { name: "Run task" });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/What should the agents work on/), {
      target: { value: "   " },
    });
    expect(button).toBeDisabled();
  });

  it("starts a run and navigates to it", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "new-id", status: "pending" }), { status: 201 }),
    );
    renderComposer();
    fireEvent.change(screen.getByLabelText(/What should the agents work on/), {
      target: { value: "Plan a study schedule" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run task" }));
    await waitFor(() => expect(screen.getByText("run page")).toBeInTheDocument());
  });

  it("tells the user how to recover when the API is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    renderComposer();
    fireEvent.change(screen.getByLabelText(/What should the agents work on/), {
      target: { value: "Plan a study schedule" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run task" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/API server is running/);
  });
});
