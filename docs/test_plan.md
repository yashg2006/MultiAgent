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

Measured by `pytest --cov=src` in CI run
[39615268359](https://github.com/yashg2006/MultiAgent/actions/runs/39615268359)
(commit `8dd82b0`). Per-area figures are aggregated from CI's per-file report.

| Module | Target | Measured (statements / missed) | Met? |
|--------|--------|-------------------------------|------|
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
