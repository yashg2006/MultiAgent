# Multi-Agent AI System

[![Python Tests](https://github.com/yashg2006/MultiAgent/actions/workflows/tests.yml/badge.svg)](https://github.com/yashg2006/MultiAgent/actions/workflows/tests.yml)

A Software Engineering course project (VIT Chennai) in which an orchestrator
coordinates three agents to work on a goal:

1. **Planner** breaks the goal into sub-tasks.
2. **Research** works on each sub-task.
3. **Validator** checks the combined result; if it fails, the orchestrator
   retries the research→validate cycle (up to 3 times by default) and otherwise
   returns a partial result with the reasons.

It ships with a FastAPI backend, a SQLite run history, and a React web UI that
shows each run's step trace, including validator retries.

## Team

- Yash Gharat (24BRS1357)
- Dhanika Bhat (24BRS1356)
- Ayushi Singh (24BRS1369)

## Quick start

Requires Python 3.10+ and Node.js 20+.

```bash
git clone https://github.com/yashg2006/MultiAgent.git
cd MultiAgent

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # optional; defaults work as-is

# Terminal 1: API on http://localhost:8000 (docs at /docs)
uvicorn src.api.main:app --reload

# Terminal 2: web UI on http://localhost:5173
cd frontend
npm install
npm run dev
```

No API key is needed: the default `LLM_PROVIDER=mock` is a deterministic,
offline stand-in for an LLM. To use Claude, set `LLM_PROVIDER=anthropic` and
`ANTHROPIC_API_KEY` in `.env`. Each run's page shows how many model calls it
made and what they cost. All options are listed in `.env.example`.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/auth/register` | Create an account `{"email", "password"}` and sign in (sets an httpOnly session cookie). |
| `POST` | `/auth/login` / `/auth/logout` | Sign in / out. |
| `GET` | `/auth/me` | The signed-in user (401 if signed out). |
| `POST` | `/tasks` | Start a run: `{"task": "..."}`. Returns immediately with `status: "pending"`. |
| `GET` | `/tasks/{id}` | A run's status, findings, retry count, usage, and steps so far. |
| `GET` | `/tasks/{id}/events` | Live step stream (Server-Sent Events); resumes with `Last-Event-ID`. |
| `POST` | `/tasks/{id}/cancel` | Stop a queued or running run after its current step (409 if finished). |
| `GET` | `/tasks` | Recent runs, newest first. |
| `GET` | `/health` | Liveness check. |
| `GET` | `/ready` | Readiness: database and queue reachable (503 otherwise). |
| `GET` | `/metrics` | Prometheus metrics for this API process. |
| `GET` | `/tasks/stats/summary` | The signed-in user's run totals, success rate, and model usage. |

All `/tasks` routes require sign-in and only return your own runs.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `LLM_PROVIDER` | `mock` | `mock` (free, offline), `anthropic`, or `openai` |
| `ANTHROPIC_API_KEY` | (empty) | Required when `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | Claude model to use |
| `OPENAI_API_KEY` | (empty) | Required when `LLM_PROVIDER=openai` (`pip install openai`) |
| `SEARCH_TOOL` | `none` | `wikipedia` grounds research in free Wikipedia search |
| `MAX_RETRIES` | `3` | Validation attempts before returning a partial result |
| `JUDGE_THRESHOLD` | `0.6` | Minimum 0–1 quality score from the validator's LLM judge |
| `LLM_MAX_ATTEMPTS` | `3` | Attempts per model call on transient errors (with backoff) |
| `DATABASE_URL` | `sqlite:///./tasks.db` | Where runs are stored (Postgres: `postgresql+psycopg://...`) |
| `QUEUE_BACKEND` | `inline` | `inline` runs tasks in the API process; `redis` hands them to workers |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for `QUEUE_BACKEND=redis` |
| `AUTO_MIGRATE` | `true` | Apply database migrations when the API starts |
| `JWT_SECRET` | (random per process) | Session signing key; **required** when `ENV=production` |
| `COOKIE_SECURE` | `false` | Send the session cookie over HTTPS only (enable behind TLS) |
| `LOG_FORMAT` | `text` | `json` emits one JSON log object per line |
| `WORKER_METRICS_PORT` | `9100` | Port each worker serves its Prometheus metrics on |
| `CORS_ORIGINS` | `http://localhost:5173` | Browser origins allowed to call the API (comma-separated) |
| `VITE_API_URL` | (empty) | Frontend only: API base URL for a deployed build; the dev server proxies to port 8000 |

## Tests

```bash
pytest --cov=src                  # backend
cd frontend && npm test           # frontend
```

CI runs lint (ruff, black), type checks (mypy, tsc), both test suites, and a
production frontend build on every pull request, then re-runs the database and
queue tests against real Postgres and Redis, and posts coverage on the PR.

## Running with workers

By default tasks run inside the API process. To run them on separate workers
(what production uses), start Redis and set `QUEUE_BACKEND=redis` for both
processes:

```bash
uvicorn src.api.main:app            # API
arq src.worker.main.WorkerSettings  # one or more workers
```

The schema is managed by Alembic (`migrations/`); `alembic upgrade head`
applies it, and the API does so on startup unless `AUTO_MIGRATE=false`.
Measured results are recorded in [`docs/test_plan.md`](docs/test_plan.md).

## Repository layout

```
src/orchestrator/   pipeline coordination, retries, aggregation
src/agents/         Planner, Research, Validator (shared Agent base class)
src/shared/         schemas, config, LLM provider, retry helper, database
src/api/            FastAPI app
frontend/           React UI
tests/              pytest suite
docs/               SRS, architecture, test plan, sprint logs, reports
```

Contribution workflow: see [CONTRIBUTING.md](CONTRIBUTING.md).
