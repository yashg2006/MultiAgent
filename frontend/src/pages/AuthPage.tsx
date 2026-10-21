import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuthAction, useMe } from "../hooks/useAuth";

const COPY = {
  signin: {
    title: "Sign in",
    action: "Sign in",
    pending: "Signing in…",
    switchText: "New here?",
    switchLink: "Create an account",
    switchTo: "/register",
  },
  register: {
    title: "Create an account",
    action: "Create account",
    pending: "Creating account…",
    switchText: "Already have an account?",
    switchLink: "Sign in",
    switchTo: "/login",
  },
} as const;

const inputClass =
  "w-full rounded-md border border-rule bg-white px-3 py-2 text-sm text-ink focus:border-action focus:outline-none focus:ring-2 focus:ring-action/30";

export function AuthPage({ mode }: { mode: "signin" | "register" }) {
  const copy = COPY[mode];
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const me = useMe();
  const action = useAuthAction(mode);
  const returnTo = (location.state as { from?: string } | null)?.from ?? "/";

  if (me.data) return <Navigate to={returnTo} replace />;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    action.mutate({ email, password }, { onSuccess: () => navigate(returnTo, { replace: true }) });
  }

  return (
    <div className="flex min-h-screen items-start justify-center bg-panel px-4 pt-24 font-sans text-ink">
      <main className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <p className="text-sm text-steel">Multi-Agent Runs</p>
          <h1 className="text-2xl font-semibold">{copy.title}</h1>
        </div>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby={mode === "register" ? "password-hint" : undefined}
              className={inputClass}
            />
            {mode === "register" && (
              <p id="password-hint" className="text-xs text-steel">
                At least 8 characters.
              </p>
            )}
          </div>
          {action.isError && (
            <p role="alert" className="text-sm text-fail">
              {action.error.message}
            </p>
          )}
          <button
            type="submit"
            disabled={action.isPending || !email || !password}
            className="w-full rounded-md bg-action px-4 py-2 text-sm font-medium text-white hover:bg-action-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:cursor-not-allowed disabled:opacity-50"
          >
            {action.isPending ? copy.pending : copy.action}
          </button>
        </form>
        <p className="text-sm text-steel">
          {copy.switchText}{" "}
          <Link
            to={copy.switchTo}
            state={location.state}
            className="font-medium text-action underline-offset-4 hover:underline"
          >
            {copy.switchLink}
          </Link>
        </p>
      </main>
    </div>
  );
}
