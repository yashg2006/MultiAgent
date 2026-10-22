# Test Plan

## Multi-Agent AI System

---

| Field | Details |
|---|---|
| **Document Version** | 1.0 |
| **Date** | [DD/MM/YYYY] |
| **Prepared By** | [Student Name 3] |
| **Reviewed By** | [Student Name 1], [Student Name 2] |
| **Faculty Guide** | Prof. [Faculty Name] |

---

## 1. Introduction

### 1.1 Purpose

This document defines the test plan, test strategy, and test cases for the Multi-Agent AI System. It covers unit testing, integration testing, and system testing to ensure the system meets all functional and non-functional requirements defined in the SRS.

### 1.2 Scope

| In Scope | Out of Scope |
|----------|-------------|
| Unit tests for all agent modules | Load/stress testing |
| Unit tests for shared utilities and schemas | Security penetration testing |
| Integration tests for orchestrator-agent pipeline | UI testing (no UI in current scope) |
| System tests for end-to-end task execution | Performance benchmarking under production load |
| CI/CD pipeline validation (GitHub Actions) | |

---

## 2. Test Strategy

### 2.1 Testing Levels

| Level | Description | Responsibility |
|-------|-------------|----------------|
| **Unit Testing** | Test individual functions and methods in isolation using mocks for external dependencies. | All team members (per module ownership) |
| **Integration Testing** | Test the interaction between Orchestrator and Agents with mocked LLM APIs. | [Student Name 1] |
| **System Testing** | Test the complete pipeline end-to-end with real or sandbox API calls. | [Student Name 3] |

### 2.2 Test Tools and Frameworks

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner and assertion framework |
| `pytest-cov` | Code coverage measurement |
| `unittest.mock` / `pytest-mock` | Mocking external API calls and agent dependencies |
| GitHub Actions | Automated test execution on push/PR |

### 2.3 Entry and Exit Criteria

**Entry Criteria:**
- Source code for the module under test is committed and compiles without errors.
- Test data and mock fixtures are prepared.

**Exit Criteria:**
- All planned test cases are executed.
- All critical and high-priority test cases pass.
- Code coverage meets the minimum threshold (target: ≥ 70% overall; see §6).

---

## 3. Test Cases

> **How these results were obtained:** every "Pass" below is from a real `pytest` run
> in GitHub Actions (`.github/workflows/tests.yml`, Python 3.10, `ubuntu-latest`) on
> 21/10/2026 — run [39615268359](https://github.com/yashg2006/MultiAgent/actions/runs/39615268359)
> on commit `8dd82b0` (branch `feature/minimal-api`), all steps green (ruff, black,
> mypy, pytest). The suite contains 51 test functions (53
> collected cases, counting one 3-way parametrized test) across `tests/`.
>
> History, for honesty: Phases A-C were first checked by direct execution of the real
> source in a no-network dev sandbox (pytest could not be installed there), then
> confirmed by CI. Phase D's API tests could not be run in that sandbox at all; their
> **first CI run failed** at the mypy step (legacy SQLAlchemy `Column(...)` typing,
> invisible locally because SQLAlchemy was not installed). That was fixed by moving
> to SQLAlchemy 2.0 `Mapped[...]` declarations, after which the full suite passed.

### 3.1 Unit Test Cases — Orchestrator

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-O-01 | Orchestrator initialises without errors | N/A | `Orchestrator` object created, `agents` = {planner, research, validator} | Matched | Pass |
| UT-O-02 | `run()` returns a successful `RunResult` for a valid task | `"sample task"` | `RunResult(status="success", result={...})` | `status="success"`, 3 sub-task results, `retries_used=0` | Pass |
| UT-O-03 | `run()` handles empty input gracefully | `""` | Error, not a crash | `status="error"`, `error="input_task must not be empty."` | Pass |
| UT-O-04 | Retry logic triggers on validator rejection | Always-failing Validator double, `max_retries=2` | Retry twice, then `status="partial"` | `status="partial"`, `retries_used=2`, reasons preserved | Pass |

### 3.2 Unit Test Cases — Research Agent

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-R-01 | `execute()` returns `AgentResponse` with findings | `AgentRequest(prompt="test query")` | `status="success"`, `result.findings` present | `status="success"`, `result={"query": "test query", "findings": "[mock-response:...] test query"}` | Pass |
| UT-R-02 | `execute()` handles empty query | `AgentRequest(prompt="")` | `status="error"`, no exception raised | `status="error"`, `error="Research query must not be empty."` | Pass |
| UT-R-03/04 | Agent initialises with/without explicit config | `ResearchAgent()` / `ResearchAgent(config={...})` | Agent object with `config={}` / given dict | Confirmed both paths | Pass |

### 3.3 Unit Test Cases — Planner Agent

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-P-01/02 | `create_plan()` returns a `Plan` with structured `SubTask`s | `"test objective"` | `Plan` with 3 `SubTask`s (id + description) | `plan.sub_tasks` = `[st-1, st-2, st-3]`, each with a description | Pass |
| UT-P-03 | `create_plan()`/`execute()` handles empty input | `AgentRequest(prompt="")` | `status="error"` | `status="error"` | Pass |

### 3.4 Unit Test Cases — Validator Agent

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-V-01 | `validate()` passes well-formed, non-empty results | `{"st-1": {"findings": "ok"}}` | `ValidationStatus.PASS` | `ValidationStatus.PASS` | Pass |
| UT-V-02 | `validate()` fails on an empty or error-flagged sub-task | `{"st-1": {}}` | `ValidationStatus.FAIL`, reason naming `st-1` | `FAIL`, reasons=`["'st-1' is empty", "judge: ..."]` | Pass |
| UT-V-03 | `validate()` handles an empty dict | `{}` | `ValidationStatus.FAIL` (nothing to validate) | `FAIL` | Pass |

### 3.5 Unit Test Cases — Shared Module

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-S-01 | `AgentRequest` schema validates correct data | Valid fields | Pydantic model created | Created successfully | Pass |
| UT-S-02 | `AgentRequest` rejects missing required fields | Dict missing `task_id` | `ValidationError` raised | `pydantic.ValidationError` raised | Pass |
| UT-S-03 | `AgentResponse` accepts optional fields as None | Only required fields given | Model created with `result=None` | `result=None`, `error=None` | Pass |
| UT-S-04 | `setup_logger()` returns a logger instance, no duplicate handlers on repeat calls | `"test_logger"` (called twice) | `logging.Logger` instance, 1 handler | Instance returned, `len(handlers) == 1` on 2nd call | Pass |
| UT-S-05 | `Settings` loads default values with no `.env` | `Settings(_env_file=None)` | Defaults applied | `app_name="MultiAgentAISystem"`, `llm_provider="mock"`, `max_retries=3` | Pass |
| UT-RT-01..06 | Retry helper: first-try success, retry-then-succeed, exhausted raises `RetryExhaustedError`, exponential backoff timing, unlisted exception not retried, `max_retries<1` rejected | See `tests/test_retry.py` | See `tests/test_retry.py` | All behaviors confirmed via direct execution (see commit history) | Pass |

### 3.6 Integration Test Cases

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| IT-01 | Orchestrator dispatches to Planner and receives plan | `"Plan a research project"` | Planner runs first; Orchestrator processes sub-tasks | `step_names[0] == "planner"` | Pass |
| IT-02 | Orchestrator dispatches to Research Agent for each sub-task | Default plan (3 sub-tasks) | 3 research steps dispatched | 3 `research` steps observed | Pass |
| IT-03 | Orchestrator sends aggregated results to Validator | Aggregated research results | Validator runs last, returns pass/fail | `step_names[-1] == "validator"` | Pass |
| IT-04 | Full pipeline executes without exceptions (Mock provider) | Complete task input | Final aggregated `RunResult` returned | `status="success"`, no exception | Pass |
| IT-05 | Pipeline handles agent failure mid-execution | Research Agent double that always raises, `max_retries=2` | Graceful handling, `status="partial"` after retries exhausted | `status="partial"`, `retries_used=2`, every sub-task entry carries `error` | Pass |
| IT-06 | Planner failure short-circuits the pipeline | Planner double returning `status="error"` | `status="error"`, Research/Validator never dispatched | `status="error"`, `steps == ["planner"]` | Pass |

### 3.7a API Test Cases (Phase D, `tests/test_api.py`)

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| API-01 | `GET /health` returns ok | N/A | `{"status": "ok"}`, HTTP 200 | As expected (CI) | Pass |
| API-02 | `POST /tasks` creates a task and the background run completes | `{"task": "..."}` | HTTP 201 `status="pending"`, then `GET` shows `status="success"` | As expected (CI) | Pass |
| API-03 | `POST /tasks` rejects an empty task string | `{"task": ""}` | HTTP 422 | As expected (CI) | Pass |
| API-04 | `GET /tasks/{id}` on an unknown id | Random id | HTTP 404 | As expected (CI) | Pass |
| API-05 | `GET /tasks` lists tasks most-recent-first | 2 created tasks | Second task's id appears before the first's | As expected (CI) | Pass |

### 3.7b LLM Provider Test Cases (`tests/test_llm_provider.py`)

| Test ID | Test Description | Expected Output | Status |
|---------|-----------------|-----------------|--------|
| LLM-01 | `get_provider("mock")` (any case/whitespace) | `MockLLMProvider` | Pass |
| LLM-02 | `get_provider("openai")` with no key | `RuntimeError` naming `OPENAI_API_KEY` | Pass |
| LLM-03 | `get_provider("<unknown>")` | `ValueError` | Pass |
| LLM-04 | Mock `complete()` is deterministic and prompt-dependent | Same in → same out; different in → different out | Pass |
| LLM-05 | Mock `complete_json()` | Structured dict with 8-char digest | Pass |
| LLM-06..08 | `OpenAIProvider` via an injected fake `openai` module (offline) | Correct client/key wiring; system+user messages sent; system message omitted when not given | Pass |
| LLM-09..10 | `safe_json_loads` | Dict for JSON objects; `None` for invalid JSON, arrays, `None` | Pass |

### 3.7c API CORS and Frontend Test Cases (Phase E)

Results from CI run [39616185724](https://github.com/yashg2006/MultiAgent/actions/runs/39616185724)
(PR #3, commit `6d3b101`): Python job green; frontend job green — `tsc` clean, **17/17
vitest tests passed**, and `vite build` succeeded (JS 214.50 kB / 69.10 kB gzip, CSS 12.23 kB).

| Test ID | Test Description | Expected Output | Status |
|---------|-----------------|-----------------|--------|
| API-06 | CORS preflight from the configured dev origin | `access-control-allow-origin: http://localhost:5173` | Pass |
| API-07 | Request from an unlisted origin | No `access-control-allow-origin` header | Pass |
| FE-01..03 | `groupSteps` splits planner / research→validator attempts, keeps an open trailing attempt, handles planner-only runs | Correct grouping | Pass |
| FE-04..07 | `RunTrace`: retried vs. final rejected attempt labels, latency in ms, step error detail, empty state | Rendered as specified | Pass |
| FE-08..09 | `parseApiTime`: zone-less timestamps read as UTC; explicit offsets respected | Correct UTC instant | Pass |
| FE-10..11 | `taskToMarkdown`: goal, status, problem, findings, failed sub-task, step table | Expected Markdown | Pass |
| FE-12..14 | API client: JSON POST body, API `detail` surfaced, non-JSON error falls back to status | As specified | Pass |
| FE-15..17 | `TaskComposer`: disabled until a goal is typed, submits and navigates, shows recovery hint when the API is unreachable | As specified | Pass |

### 3.7d Real-LLM Path Test Cases (Phase F1)

From CI run [39623939397](https://github.com/yashg2006/MultiAgent/actions/runs/39623939397)
(PR #4): all pass. No real model is called; providers are scripted fakes or a
fake Anthropic SDK module. Backend suite: 107 test functions; frontend: 21/21.

| Test ID | Area (file) | What is verified | Status |
|---------|-------------|------------------|--------|
| RES-01..05 | Circuit breaker (`test_resilience.py`) | Opens at threshold and fails fast without calling the provider; half-open trial closes on success / re-opens on failure; success resets the count | Pass |
| RES-06..09 | Resilient LLM calls (`test_resilience.py`) | Transient errors retried and counted (3 calls, 2 retries); non-transient errors not retried; gives up after `LLM_MAX_ATTEMPTS`; open circuit stops further calls | Pass |
| LLM-11..21 | Providers (`test_llm_provider.py`) | Anthropic: SDK retries disabled, timeout set, text blocks joined, usage read, only transient error types retried, configured model used, key required; Mock plan/judge JSON; cost table incl. unknown model = $0; shared provider cache; JSON extraction from fenced/prose output | Pass |
| PLN-01..13 | Planner (`test_planner.py`) | Parses fenced JSON with `depends_on`; states the sub-task limit; one repair attempt then a clean error; provider failure reported, not raised; rejects empty, duplicate, unknown/self dependency, cyclic, blank, over-limit plans | Pass |
| VAL-01..10 | Validator (`test_validator.py`) | Judge score ≥ threshold passes, below fails with reasons; threshold configurable; prompt includes objective and findings; rule failures skip the judge; unusable/out-of-range score or judge outage falls back to rule verdict | Pass |
| SRC-01..07 | Search + Research (`test_search.py`) | Wikipedia hits parsed, markup stripped, User-Agent sent; network errors / bad payloads / blank queries give no hits; research prompt includes hits, dependency context and retry feedback; sources returned | Pass |
| ORC-06..13 | Orchestrator (`test_orchestrator.py`) | Dependency levels and cycle fallback; dependent sub-task receives prior findings; every step streamed; failing observer ignored; cancellation keeps partial results; retry carries validator feedback; usage totalled; supplied task id used | Pass |
| API-08 | API (`test_api.py`) | Completed task reports usage totals (Mock: 5 calls, $0) | Pass |
| FE-18..21 | Frontend (`usage.test.ts`) | Usage wording: none, calls-only for Mock, retries/tokens/cost, tiny costs shown as "under $0.01" | Pass |

### 3.7e Infrastructure Test Cases (Phase F2)

From CI run [39626141696](https://github.com/yashg2006/MultiAgent/actions/runs/39626141696)
(PR #5): all pass. The database and queue suites ran twice — on SQLite, and
again on Postgres 16 with Redis 7 service containers (**35/35 passed, 0
skipped**, including the real Redis round trip). Backend: 133 test functions;
frontend: 27/27.

| Test ID | Area (file) | What is verified | Status |
|---------|-------------|------------------|--------|
| MIG-01..02 | Migrations (`test_migrations.py`) | `alembic check` finds no drift between models and migrations; downgrade to base removes the tables and upgrade restores them | Pass |
| WRK-01..07 | Pipeline runner (`test_worker.py`) | Runs and persists steps (seq 1..5) and result; steps visible while the run is still `running`; cancelled-while-queued never starts; cancel mid-run stops between stages; second delivery is a no-op; unknown task ignored; crash recorded as `error` | Pass |
| WRK-08..11 | Queue (`test_worker.py`) | arq job function runs a task; inline queue schedules after the response; Redis queue enqueues with job id = task id, reports health, closes; unknown backend rejected | Pass |
| WRK-12 | Redis round trip (`test_worker.py`, integration pass only) | Enqueue twice → Redis → arq worker (burst) → task `success` with 5 steps (duplicate ignored) | Pass |
| API-09..21 | API (`test_api.py`) | Blank/over-long input → 422; input trimmed; steps returned in order with seq; list omits steps; SSE replays steps then `status` and `done`; resume after `Last-Event-ID`; 404 for unknown stream/cancel; 409 cancelling a finished run; cancel sets the flag on a queued run; `/ready` 200, and 503 when the database is unreachable | Pass |
| FE-22..27 | Frontend (`useTaskStream.test.tsx`, `RunTrace.test.tsx`) | Stream opens the run's URL and merges steps without duplicates; status and done applied, stream closed; reconnecting state; closed on disable/unmount; empty live trace; no "retries exhausted" claim while live | Pass |

### 3.7f Accounts and Access Test Cases (Phase F3)

From CI run [39627228463](https://github.com/yashg2006/MultiAgent/actions/runs/39627228463)
(PR #6): all pass; backend 151 test functions, coverage **98% (1274 statements,
29 missed)** with `src/api/auth.py` at 100% and `src/api/rate_limit.py` at 98%;
frontend 31/31. All existing API tests now run as a signed-in user.

| Test ID | What is verified (`test_auth.py`, `auth.test.tsx`) | Status |
|---------|------------------|--------|
| AUTH-01..06 | Registration sets an httpOnly, SameSite=Strict cookie and never echoes the password; email normalised and duplicates rejected (409); invalid email, short password and >72-byte password rejected (422) | Pass |
| AUTH-07..10 | Sign-in/sign-out round trip; logout expires the cookie; wrong password and unknown email get the identical 401; hashes are salted and verify correctly | Pass |
| AUTH-11..15 | All task routes and `/auth/me` return 401 when signed out; tampered and expired tokens rejected; token for a deleted user rejected; production refuses to start without `JWT_SECRET`; development key is random but stable per process | Pass |
| AUTH-16 | Isolation: a second user sees an empty list and 404 for the first user's run, stream and cancel; the owner still sees it | Pass |
| AUTH-17..21 | Sign-in attempts limited per IP (401, 401, 429); runs limited per user with `Retry-After`; in-memory window resets each minute; Redis limiter counts and expires keys; `X-Forwarded-For` trusted only when configured | Pass |
| FE-28..31 | `getMe` returns null when signed out; signed-out visitors redirected to sign-in; sign-in returns to the app showing the user; API validation messages shown as plain sentences | Pass |

### 3.7g Observability Test Cases (Phase F4)

From CI run [39711239713](https://github.com/yashg2006/MultiAgent/actions/runs/39711239713)
(PR #7): all pass; backend coverage **98% (1436 statements, 33 missed)** with
`src/api/middleware.py` 100% and `src/shared/observability.py` 98%; 66-case
Postgres/Redis integration pass; frontend 34/34.

| Test ID | What is verified (`test_observability.py`, `test_api.py`, `MetricsPage.test.tsx`) | Status |
|---------|------------------|--------|
| OBS-01..06 | ContextFilter attaches request/task ids; JSON formatter emits one object with ids and extras and omits unset ids; text formatter includes ids only when set; record_step counts calls and validator verdicts; record_run counts by status | Pass |
| OBS-07..10 | `/metrics` returns Prometheus text with `http_requests_total` and `pipeline_runs_total`; every response carries an `X-Request-ID`; a supplied `X-Request-ID` is echoed | Pass |
| OBS-11..12 | `/tasks/stats/summary` aggregates only the signed-in user's runs (totals, success rate, usage) and requires sign-in | Pass |
| FE-32..33 | Metrics page invites a first run when empty; shows totals, success rate, and outcome counts | Pass |

### 3.7 System Test Cases

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| ST-01 | End-to-end execution with live/sandbox LLM API | Real task string, `LLM_PROVIDER=openai` | Complete, validated result | Not yet run — requires a real `OPENAI_API_KEY`; out of scope until Phase F per the project's phased build plan | Not Run |
| ST-02 | System recovers from API rate limiting | Rapid consecutive tasks against a live provider | Retry and eventual success | Not yet run — same dependency as ST-01 | Not Run |
| ST-03 | System loads configuration from `.env` correctly | Valid `.env` file | Settings populated from file | Verified the `_env_file`-override path (UT-S-05); a literal `.env`-file read was not separately exercised | Pass (partial) |

---

## 4. Test Execution Schedule

| Sprint | Testing Activity | Test Cases |
|--------|-----------------|------------|
| Sprint 3 (Weeks 5–7) | Unit tests for Orchestrator and Research Agent | UT-O-*, UT-R-* |
| Sprint 4 (Weeks 8–10) | Unit tests for Planner, Validator, and Shared modules | UT-P-*, UT-V-*, UT-S-* |
| Sprint 5 (Weeks 11–12) | Integration tests for full pipeline | IT-* |
| Sprint 6 (Weeks 13–14) | System tests and regression testing | ST-* |

---

## 5. Defect Management

| Severity | Definition | Response |
|----------|-----------|----------|
| Critical | System crash or data corruption | Fix immediately; block release |
| High | Major feature broken | Fix within current sprint |
| Medium | Minor feature issue or workaround available | Fix in next sprint |
| Low | Cosmetic or documentation issue | Fix when convenient |

---

## 6. Code Coverage — Target vs. Measured

Table below: CI run
[39623939397](https://github.com/yashg2006/MultiAgent/actions/runs/39623939397)
(PR #4, Phase F1). Latest: run
[39626141696](https://github.com/yashg2006/MultiAgent/actions/runs/39626141696)
(PR #5, Phase F2) measured **97% overall (1068 statements, 28 missed)**; the new
modules: `src/api/` 94.2% (224 / 13), `src/worker/` 95.9% (73 / 3),
`src/shared/db.py` 100% (78 / 0). Per-area figures are aggregated from CI's per-file report.

| Module | Target | Measured (statements / missed) | Met? |
|--------|--------|-------------------------------|------|
| `src/orchestrator/` | ≥ 70% | 98.3% (121 / 2) | Yes |
| `src/agents/research_agent/` | ≥ 70% | 93.2% (44 / 3) | Yes |
| `src/agents/planner_agent/` | ≥ 70% | 97.5% (81 / 2) | Yes |
| `src/agents/validator_agent/` | ≥ 70% | 98.4% (63 / 1) | Yes |
| `src/agents/base.py` | — | 92.9% (14 / 1) | — |
| `src/shared/` | ≥ 80% | 99.2% (396 / 3) | Yes |
| `src/api/` | — | 91.7% (109 / 9) | — |
| **Overall** | **≥ 70%** | **97.5% (828 / 21)** | **Yes** |

History: 90% at the first measured run (Phase D), 95% after targeted LLM
provider tests, 97.5% after Phase F1 (which roughly doubled the code size).
Remaining misses are mostly defensive branches (e.g. the background-task
crash handler in `src/api/routes.py`).

--------|--------|-------------------------------|------|
| `src/orchestrator/` | ≥ 70% | 98.6% (69 / 1) | Yes |
| `src/agents/research_agent/` | ≥ 70% | 82.4% (17 / 3) | Yes |
| `src/agents/planner_agent/` | ≥ 70% | 87.0% (23 / 3) | Yes |
| `src/agents/validator_agent/` | ≥ 70% | 91.4% (35 / 3) | Yes |
| `src/agents/base.py` | — | 92.3% (13 / 1) | — |
| `src/shared/` | ≥ 80% | 99.4% (165 / 1) | Yes |
| `src/api/` (added in Phase D) | — | 90.5% (95 / 9) | — |
| **Overall** | **≥ 70%** | **95.0% (417 / 21)** | **Yes** |

The first measured run (before `tests/test_llm_provider.py` was added) was 90%
overall, with `src/shared/llm_provider.py` at 48% as the weakest module; the
targeted tests raised it to 98%. Most remaining misses are defensive
provider-error branches inside the agents and the background-task crash
handler in `src/api/routes.py`.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [DD/MM/YYYY] | [Student Name 3] | Initial test plan |
| 1.1 | 21/10/2026 | Yash Gharat (with Claude Code) | Filled test-case results from CI; added API (§3.7a) and LLM provider (§3.7b) cases; recorded measured coverage (§6) |
| 1.2 | 21/10/2026 | Yash Gharat (with Claude Code) | Added Phase E (§3.7c) and Phase F1 (§3.7d) cases; coverage refreshed to 97.5% |
| 1.3 | 21/10/2026 | Yash Gharat (with Claude Code) | Added Phase F2 infrastructure cases (§3.7e), incl. Postgres/Redis integration pass |
| 1.4 | 21/10/2026 | Yash Gharat (with Claude Code) | Added Phase F3 accounts and access cases (§3.7f) |
| 1.5 | 22/10/2026 | Yash Gharat (with Claude Code) | Added Phase F4 observability cases (§3.7g); coverage 98% |
