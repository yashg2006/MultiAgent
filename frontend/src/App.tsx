import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { TaskComposer } from "./components/TaskComposer";
import { TaskHistory } from "./components/TaskHistory";
import { BrandMark } from "./components/BrandMark";
import { useMe, useSignOut } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { MetricsPage } from "./pages/MetricsPage";
import { StartPage } from "./pages/StartPage";
import { TaskPage } from "./pages/TaskPage";

function Shell() {
  const me = useMe();
  const signOut = useSignOut();
  const location = useLocation();

  if (me.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        Loading…
      </div>
    );
  }
  if (me.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <p role="alert" className="max-w-sm text-sm text-fail">
          Couldn't reach the server ({me.error.message}). Check that the API is running, then
          reload.
        </p>
      </div>
    );
  }
  if (!me.data) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return (
    <div className="min-h-screen font-sans text-ink">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-6 md:grid-cols-[21rem_1fr] md:px-8 md:py-10">
        <aside className="flex flex-col gap-7 md:sticky md:top-10 md:self-start md:max-h-[calc(100vh-5rem)]">
          <Link
            to="/"
            className="flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
          >
            <BrandMark />
            <span className="font-display text-[1.05rem] font-semibold leading-none tracking-tight">
              Multi-Agent&nbsp;Runs
            </span>
          </Link>

          <TaskComposer />

          <section className="min-h-0 flex-1 flex flex-col">
            <div className="mb-2.5 flex items-baseline justify-between">
              <h2 className="font-display text-sm font-medium text-ink">Recent runs</h2>
              <Link
                to="/stats"
                className="rounded text-xs font-medium text-muted underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
              >
                Stats
              </Link>
            </div>
            <div className="-mr-1 min-h-0 flex-1 overflow-y-auto pr-1">
              <TaskHistory />
            </div>
          </section>

          <div className="flex items-center justify-between gap-3 border-t border-line pt-4 text-xs text-muted">
            <span className="truncate" title={me.data.email}>
              {me.data.email}
            </span>
            <button
              type="button"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
              className="shrink-0 rounded font-medium text-muted underline-offset-4 hover:text-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
            >
              Sign out
            </button>
          </div>
        </aside>

        <main className="min-w-0 border-t border-line pt-8 md:border-l md:border-t-0 md:pl-10 md:pt-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="login" element={<AuthPage mode="signin" />} />
      <Route path="register" element={<AuthPage mode="register" />} />
      <Route element={<Shell />}>
        <Route index element={<StartPage />} />
        {/* Run pages live under /runs, not /tasks: /tasks/* is the API, and sharing
            one path made reloads and shared links return JSON. */}
        <Route path="runs/:id" element={<TaskPage />} />
        <Route path="stats" element={<MetricsPage />} />
      </Route>
    </Routes>
  );
}
