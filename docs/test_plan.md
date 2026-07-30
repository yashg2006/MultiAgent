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
- Code coverage meets the minimum threshold ([target: 70%+]).

---

## 3. Test Cases

### 3.1 Unit Test Cases — Orchestrator

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-O-01 | Orchestrator initialises without errors | N/A | `Orchestrator` object is created successfully | [Fill] | [Pass/Fail] |
| UT-O-02 | `run()` returns a dict result for a valid task | `"sample task"` | Dict with result data | [Fill] | [Pass/Fail] |
| UT-O-03 | `run()` handles empty input gracefully | `""` | Error message or empty result | [Fill] | [Pass/Fail] |
| UT-O-04 | Retry logic triggers on agent failure | Simulated agent exception | Retry up to 3 times, then error | [Fill] | [Pass/Fail] |

### 3.2 Unit Test Cases — Research Agent

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-R-01 | `execute()` returns dict with `status` key | `"test query"` | `{"status": ..., "query": "test query"}` | [Fill] | [Pass/Fail] |
| UT-R-02 | `execute()` handles empty query | `""` | Dict with error or empty result | [Fill] | [Pass/Fail] |
| UT-R-03 | Agent initialises with config | `{"api_key": "test"}` | Agent object with config set | [Fill] | [Pass/Fail] |
| UT-R-04 | Agent initialises without config (defaults) | `None` | Agent object with `config=None` | [Fill] | [Pass/Fail] |

### 3.3 Unit Test Cases — Planner Agent

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-P-01 | `create_plan()` returns a list | `"test objective"` | `list` instance | [Fill] | [Pass/Fail] |
| UT-P-02 | Plan contains structured sub-tasks | `"complex objective"` | List of dicts with `description` keys | [Fill] | [Pass/Fail] |
| UT-P-03 | `create_plan()` handles empty input | `""` | Empty list or error | [Fill] | [Pass/Fail] |

### 3.4 Unit Test Cases — Validator Agent

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-V-01 | `validate()` returns True for valid data | `{"result": "data"}` | `True` | [Fill] | [Pass/Fail] |
| UT-V-02 | `validate()` returns False for invalid data | `{"invalid": None}` | `False` | [Fill] | [Pass/Fail] |
| UT-V-03 | `validate()` handles empty dict | `{}` | `True` (or configurable) | [Fill] | [Pass/Fail] |

### 3.5 Unit Test Cases — Shared Module

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| UT-S-01 | `AgentRequest` schema validates correct data | Valid dict | Pydantic model created | [Fill] | [Pass/Fail] |
| UT-S-02 | `AgentRequest` rejects missing required fields | Dict missing `task_id` | `ValidationError` raised | [Fill] | [Pass/Fail] |
| UT-S-03 | `AgentResponse` accepts optional fields as None | Dict with only required fields | Model created with `result=None` | [Fill] | [Pass/Fail] |
| UT-S-04 | `setup_logger()` returns a logger instance | `"test_logger"` | `logging.Logger` instance | [Fill] | [Pass/Fail] |
| UT-S-05 | `Settings` loads default values | No `.env` file | Settings with default `app_name` | [Fill] | [Pass/Fail] |

### 3.6 Integration Test Cases

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| IT-01 | Orchestrator dispatches to Planner and receives plan | Mock task | Planner returns sub-task list; Orchestrator processes it | [Fill] | [Pass/Fail] |
| IT-02 | Orchestrator dispatches to Research Agent for each sub-task | Mock plan with 3 sub-tasks | 3 research results returned | [Fill] | [Pass/Fail] |
| IT-03 | Orchestrator sends aggregated results to Validator | Mock aggregated results | Validation pass/fail returned | [Fill] | [Pass/Fail] |
| IT-04 | Full pipeline executes without exceptions (mocked APIs) | Complete task input | Final aggregated result returned | [Fill] | [Pass/Fail] |
| IT-05 | Pipeline handles agent failure mid-execution | Simulated agent crash | Graceful error handling, partial result | [Fill] | [Pass/Fail] |

### 3.7 System Test Cases

| Test ID | Test Description | Input | Expected Output | Actual Output | Status |
|---------|-----------------|-------|-----------------|---------------|--------|
| ST-01 | End-to-end execution with live/sandbox API | Real task string | Complete, validated result | [Fill] | [Pass/Fail] |
| ST-02 | System recovers from API rate limiting | Rapid consecutive tasks | Retry and eventual success | [Fill] | [Pass/Fail] |
| ST-03 | System loads configuration from `.env` correctly | Valid `.env` file | Settings populated | [Fill] | [Pass/Fail] |

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

## 6. Code Coverage Target

| Module | Target Coverage |
|--------|----------------|
| `src/orchestrator/` | ≥ 70% |
| `src/agents/research_agent/` | ≥ 70% |
| `src/agents/planner_agent/` | ≥ 70% |
| `src/agents/validator_agent/` | ≥ 70% |
| `src/shared/` | ≥ 80% |
| **Overall** | **≥ 70%** |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [DD/MM/YYYY] | [Student Name 3] | Initial test plan |
| | | | |
