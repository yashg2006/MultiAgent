import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { TaskComposer } from "./components/TaskComposer";
import { TaskHistory } from "./components/TaskHistory";
import { useMe, useSignOut } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { StartPage } from "./pages/StartPage";
import { TaskPage } from "./pages/TaskPage";

function Shell() {
  const me = useMe();
  const signOut = useSignOut();
  const location = useLocation();

  if (me.isPending) {
    return <p className="p-6 font-sans text-sm text-steel">Loading…</p>;
  }
  if (me.isError) {
    return (
      <p role="alert" className="p-6 font-sans text-sm text-fail">
        Couldn't reach the server ({me.error.message}). Check that the API is running, then reload.
      </p>
    );
  }
  if (!me.data) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return (
    <div className="min-h-screen bg-panel font-sans text-ink">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-6 md:grid-cols-[20rem_1fr] md:px-6 md:py-10">
        <aside className="space-y-8 md:sticky md:top-10 md:self-start">
          <h1 className="text-lg font-semibold">
            <Link
              to="/"
              className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-action"
            >
              Multi-Agent Runs
            </Link>
          </h1>
          <TaskComposer />
          <section>
            <h2 className="mb-2 text-sm font-medium text-steel">Past runs</h2>
            <TaskHistory />
          </section>
          <div className="flex items-center justify-between gap-3 border-t border-rule pt-4 text-xs text-steel">
            <span className="truncate">{me.data.email}</span>
            <button
              type="button"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
              className="font-medium text-action underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-action"
            >
              Sign out
            </button>
          </div>
        </aside>
        <main className="min-w-0 border-t border-rule pt-8 md:border-l md:border-t-0 md:pl-8 md:pt-0">
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
        <Route path="tasks/:id" element={<TaskPage />} />
      </Route>
    </Routes>
  );
}
