# CLAUDE.md

Guidance for working in this repository — a 3rd-year VIT Chennai Software
Engineering course project (team of 3) implementing a multi-agent AI system
with an orchestrator-agent architecture.

## Architecture

```
User task → Orchestrator → Planner Agent (decompose into sub-tasks)
                         → Research Agent (per sub-task, parallel where independent)
                         → aggregate
                         → Validator Agent (schema + rule checks)
                             pass → return result
                             fail → retry (up to N) → partial result + error
```

- `src/orchestrator/` — coordinates the pipeline above; owns retry/aggregation logic.
- `src/agents/{research,planner,validator}_agent/` — one agent per concern, each
  implementing the typed `Agent` contract in `src/agents/base.py`.
- `src/shared/` — cross-cutting: `schemas.py` (Pydantic `AgentRequest`/
  `AgentResponse` and friends), `config.py` (env-based settings), `utils.py`
  (logging), `llm_provider.py` (LLM abstraction + offline Mock provider),
  `retry.py` (backoff helper).
- `src/api/` — FastAPI app: tasks, live SSE step stream, cancel, readiness.
- `src/worker/` — `execute_task` (shared by inline mode and arq workers).
- `migrations/` — Alembic schema history; `src/shared/db.py` holds the models.
- `frontend/` — React + TypeScript + Vite + Tailwind UI (added in Phase E).

New agents are added under `src/agents/<name>/`, implement the `Agent` base
class, and are registered with the Orchestrator — without modifying
Orchestrator core logic (this is a stated non-functional requirement, see
`docs/SRS.md` NFR-02).

## Commands

```bash
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

pytest                      # run tests
pytest --cov=src            # with coverage
ruff check .                # lint
black --check .             # format check (black . to auto-format)
mypy src                    # type check
uvicorn src.api.main:app --reload   # API on :8000 (runs tasks inline by default)
arq src.worker.main.WorkerSettings  # worker, with QUEUE_BACKEND=redis
alembic upgrade head        # apply migrations; add a new file in migrations/versions
                            # for every model change (tests run `alembic check`)

cd frontend && npm install  # frontend deps (Node 20+)
npm run dev                 # UI on :5173, proxies /tasks and /health to :8000
npm test                    # vitest
npm run build               # tsc + production build
```

CI (`.github/workflows/tests.yml`) runs all of the above on every PR to
`main`/`develop` and posts coverage and frontend test counts as PR
annotations. If a sandbox can't install dependencies, open the PR and use
CI as the verification step rather than reporting unrun checks as passing.

LLM provider is selected via `LLM_PROVIDER` (`mock` by default — no API key,
no cost; `anthropic` with `ANTHROPIC_API_KEY` for Claude; `openai` also
supported). Agents must call models only through `Agent.call_llm()`, which
adds retries, the circuit breaker, and usage/cost accounting. Tests and CI
never call a real model: use `tests/fakes.py::ScriptedProvider` or the Mock.

## Conventions

- PEP 8, enforced by `ruff` + `black`.
- Every public function/class/module has a docstring.
- Type hints on all function signatures; `mypy` must pass.
- Inter-agent data only ever crosses boundaries as `AgentRequest`/
  `AgentResponse` (or schemas built on them) — never raw dicts.
- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`), one
  concern per commit. Branch naming and PR flow: see `CONTRIBUTING.md`.
- Never commit `.env`, API keys, or other secrets.

## Definition of Done

A change is done when: it has type hints and docstrings; `ruff`, `black
--check`, and `mypy` pass; it ships with tests that exercise both the happy
path and at least one failure/edge case; `pytest --cov` doesn't regress
overall coverage; and any behavior change is reflected in the relevant
`docs/*.md` file in the same PR (not deferred to a later "docs pass").

## Scope note

This is a course project, not a production system. `docs/test_plan.md` and
`docs/project_report.md` explicitly scope out load/stress testing, security
penetration testing, and production-scale multi-user deployment. Treat any
of those as a stretch addition, not a baseline requirement — see the
project's phased build plan for what's core vs. stretch.
