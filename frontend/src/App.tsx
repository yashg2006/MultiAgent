import { Link, Outlet, Route, Routes } from "react-router-dom";

import { TaskComposer } from "./components/TaskComposer";
import { TaskHistory } from "./components/TaskHistory";
import { StartPage } from "./pages/StartPage";
import { TaskPage } from "./pages/TaskPage";

function Shell() {
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
      <Route element={<Shell />}>
        <Route index element={<StartPage />} />
        <Route path="tasks/:id" element={<TaskPage />} />
      </Route>
    </Routes>
  );
}
