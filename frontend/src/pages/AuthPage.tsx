import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { BrandMark } from "../components/BrandMark";
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
  "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink shadow-sm transition-colors placeholder:text-faint focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent-ring/30";

const AGENTS = [
  { name: "Planner", dot: "bg-[#8E86F5]" },
  { name: "Research", dot: "bg-[#5AC9A3]" },
  { name: "Validator", dot: "bg-[#E8A54B]" },
];

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
    <div className="grid min-h-screen font-sans text-ink md:grid-cols-[1.05fr_1fr]">
      {/* Brand panel — the product's world, hidden on small screens. */}
      <aside className="relative hidden overflow-hidden bg-ink p-8 lg:p-12 text-white md:flex md:flex-col md:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            backgroundImage:
              "radial-gradient(60% 50% at 80% 10%, rgba(74,58,236,0.45), transparent 60%), radial-gradient(50% 50% at 10% 90%, rgba(20,157,107,0.22), transparent 60%)",
          }}
        />
        <div className="relative flex items-center gap-2.5">
          <BrandMark className="h-8 w-8" />
          <span className="font-display text-lg font-semibold tracking-tight">
            Multi-Agent&nbsp;Runs
          </span>
        </div>
        <div className="relative space-y-6">
          <h2 className="max-w-[18ch] font-display text-3xl font-semibold leading-tight tracking-tight">
            Watch an orchestrator coordinate agents, in real time.
          </h2>
          <ul className="space-y-2.5">
            {AGENTS.map((a) => (
              <li key={a.name} className="flex items-center gap-3 text-sm text-white/80">
                <span aria-hidden className={`h-2 w-2 rounded-full ${a.dot}`} />
                {a.name}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative font-mono text-xs text-white/45">
          Plan → Research → Validate → Retry
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm space-y-7">
          <div className="space-y-2">
            <div className="flex items-center gap-2 md:hidden">
              <BrandMark />
              <span className="font-display text-base font-semibold tracking-tight">
                Multi-Agent&nbsp;Runs
              </span>
            </div>
            <h1 className="font-display text-2xl font-semibold tracking-tight">{copy.title}</h1>
            <p className="text-sm text-muted">
              {mode === "signin"
                ? "Sign in to run tasks and see your run history."
                : "Create an account to start running tasks."}
            </p>
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
                <p id="password-hint" className="text-xs text-muted">
                  At least 8 characters.
                </p>
              )}
            </div>
            {action.isError && (
              <p role="alert" className="rounded-md bg-fail-soft px-3 py-2 text-sm text-fail">
                {action.error.message}
              </p>
            )}
            <button
              type="submit"
              disabled={action.isPending || !email || !password}
              className="w-full rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {action.isPending ? copy.pending : copy.action}
            </button>
          </form>

          <p className="text-sm text-muted">
            {copy.switchText}{" "}
            <Link
              to={copy.switchTo}
              state={location.state}
              className="font-medium text-accent underline-offset-4 hover:underline"
            >
              {copy.switchLink}
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
