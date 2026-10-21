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
| `POST` | `/tasks` | Start a run: `{"task": "..."}`. Returns immediately with `status: "pending"`. |
| `GET` | `/tasks/{id}` | A run's status, findings, retry count, and step trace. |
| `GET` | `/tasks` | Recent runs, newest first. |
| `GET` | `/health` | Liveness check. |

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
| `DATABASE_URL` | `sqlite:///./tasks.db` | Where runs are stored |
| `CORS_ORIGINS` | `http://localhost:5173` | Browser origins allowed to call the API (comma-separated) |
| `VITE_API_URL` | (empty) | Frontend only: API base URL for a deployed build; the dev server proxies to port 8000 |

## Tests

```bash
pytest --cov=src                  # backend
cd frontend && npm test           # frontend
```

CI runs lint (ruff, black), type checks (mypy, tsc), both test suites, and a
production frontend build on every pull request, and posts coverage on the PR.
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
