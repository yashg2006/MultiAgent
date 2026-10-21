import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ApiError, getMe } from "../api";
import { App } from "../App";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const ada = { id: "u1", email: "ada@example.com", created_at: "2026-10-21T14:00:00Z" };

describe("auth", () => {
  afterEach(() => vi.restoreAllMocks());

  it("getMe returns null when signed out and rethrows other errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({ detail: "Sign in to continue." }, 401),
    );
    expect(await getMe()).toBeNull();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResponse({ detail: "boom" }, 500));
    await expect(getMe()).rejects.toBeInstanceOf(ApiError);
  });

  it("sends signed-out visitors to the sign-in page", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ detail: "x" }, 401));
    renderApp("/tasks/abc");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("signs in and returns to the app showing the user's email", async () => {
    let signedIn = false;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url === "/auth/me") return signedIn ? jsonResponse(ada) : jsonResponse({}, 401);
      if (url === "/auth/login") {
        signedIn = true;
        return jsonResponse(ada);
      }
      if (url === "/tasks") return jsonResponse([]);
      return jsonResponse({}, 404);
    });
    renderApp("/");
    fireEvent.change(await screen.findByLabelText("Email"), {
      target: { value: "ada@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "long enough pw" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(screen.getByText("ada@example.com")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("shows the API's validation message on failed registration", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input) === "/auth/me") return jsonResponse({}, 401);
      return jsonResponse({ detail: [{ msg: "Value error, Enter a valid email address." }] }, 422);
    });
    renderApp("/register");
    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "nope" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "long enough pw" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter a valid email address.");
  });
});
