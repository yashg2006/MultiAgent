# Software Requirements Specification (SRS)

## Multi-Agent AI System

---

| Field | Details |
|---|---|
| **Document Version** | 1.0 |
| **Date** | [DD/MM/YYYY] |
| **Prepared By** | [Student Name 1], [Student Name 2], [Student Name 3] |
| **Course** | [CSE XXXX] — Software Engineering |
| **Faculty Guide** | Prof. [Faculty Name] |

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document provides a complete description of the functional and non-functional requirements for the Multi-Agent AI System. It is intended for the development team, the faculty guide, and course evaluators.

### 1.2 Scope

The Multi-Agent AI System is a Python-based application that uses an orchestrator-agent pattern to decompose, execute, and validate complex tasks through coordinated autonomous agents. The system consists of a central Orchestrator, a Research Agent, a Planner Agent, and a Validator Agent communicating through shared Pydantic schemas.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|-----------|
| LLM | Large Language Model |
| API | Application Programming Interface |
| SRS | Software Requirements Specification |
| CI/CD | Continuous Integration / Continuous Deployment |
| DFD | Data Flow Diagram |
| Agent | An autonomous software module that performs a specialised sub-task |
| Orchestrator | Central controller that coordinates agent execution |

### 1.4 References

- IEEE 830-1998, IEEE Recommended Practice for Software Requirements Specifications
- [Additional reference]

### 1.5 Overview

The remainder of this document is organised as follows: Section 2 gives an overall description of the product. Section 3 details specific functional and non-functional requirements. Section 4 provides use case descriptions and diagrams. Section 5 lists hardware and software requirements.

---

## 2. Overall Description

### 2.1 Product Perspective

The Multi-Agent AI System is a standalone application that interacts with external LLM APIs. It is not part of a larger existing system. The system is designed as a modular, extensible architecture where new agents can be added without modifying the orchestrator core.

### 2.2 Product Functions (High-Level)

1. Accept a user-defined task as input.
2. Decompose the task into a structured execution plan.
3. Execute sub-tasks via specialised agents.
4. Validate and quality-check agent outputs.
5. Aggregate results and return to the user.

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Proficiency |
|------------|-------------|----------------------|
| Developer / Researcher | Primary user who submits tasks via CLI or programmatic API | High |
| Course Evaluator | Faculty reviewing system functionality and code quality | Medium–High |
| End User (Future) | Non-technical user interacting via a web UI (future scope) | Low–Medium |

### 2.4 Operating Environment

- Python 3.10+ runtime on Windows, macOS, or Linux
- Internet connectivity for LLM API calls
- Virtual environment for dependency isolation

### 2.5 Design and Implementation Constraints

- The system must be implemented in Python.
- All inter-agent data must conform to Pydantic v2 schemas.
- API keys must never be committed to version control.
- The project must be completable within a 15-week semester by a team of 2–3 students.

### 2.6 Assumptions and Dependencies

- LLM API services remain available and within free-tier / budget limits.
- Team members have basic proficiency in Python and Git.
- The university provides internet access for API calls during development and demonstration.

---

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Orchestrator Module

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-O-01 | The orchestrator shall accept a task string as input from the user. | High |
| FR-O-02 | The orchestrator shall parse the input task and determine which agents to invoke. | High |
| FR-O-03 | The orchestrator shall dispatch sub-tasks to agents sequentially or in parallel (configurable). | High |
| FR-O-04 | The orchestrator shall aggregate agent responses into a unified output. | High |
| FR-O-05 | The orchestrator shall handle agent failures gracefully with retry logic. | Medium |
| FR-O-06 | The orchestrator shall log execution state transitions for debugging. | Medium |

#### 3.1.2 Research Agent

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-R-01 | The Research Agent shall accept a query string and return structured research results. | High |
| FR-R-02 | The Research Agent shall interface with the configured LLM provider (`src/shared/llm_provider.py`) for information synthesis; a dedicated external search/retrieval API is future scope (see §9.2 of the project report). | High |
| FR-R-03 | The Research Agent shall return results conforming to the `AgentResponse` schema. | High |
| FR-R-04 | The Research Agent shall return `status="error"` with a populated `error` field — never raise an exception — if the query is empty or the LLM provider call fails. | High |

#### 3.1.3 Planner Agent

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-P-01 | The Planner Agent shall accept a high-level objective and return an ordered list of sub-tasks. | High |
| FR-P-02 | Each sub-task in the plan shall include a unique `id` and a `description` (see `SubTask` schema). | Medium |
| FR-P-03 | The Planner Agent shall return results conforming to the `AgentResponse` schema. | High |
| FR-P-04 | The Planner Agent shall return `status="error"` with a populated `error` field if the objective is empty or the LLM provider call fails, rather than returning an empty or malformed plan. | High |

#### 3.1.4 Validator Agent

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-V-01 | The Validator Agent shall accept a result dictionary and return a `ValidationResult` with a pass/fail status. | High |
| FR-V-02 | The Validator Agent shall reject (fail) a result set if any sub-task entry is empty or carries an upstream `error` key — this is a deterministic rule check, independent of LLM availability. | High |
| FR-V-03 | The Validator Agent shall provide a list of reason strings when validation fails. | Medium |
| FR-V-04 | The Validator Agent shall additionally request a qualitative score from the configured LLM provider (LLM-judge pass); a provider failure during this pass shall not change the rule-check pass/fail verdict. | Medium |

#### 3.1.5 Shared Module

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| FR-S-01 | All inter-agent data transfer shall use `AgentRequest` and `AgentResponse` Pydantic schemas. | High |
| FR-S-02 | A centralised logger utility shall be available to all modules. | Medium |
| FR-S-03 | Application configuration shall be loaded from environment variables via `.env` file. | High |

### 3.2 Non-Functional Requirements

| Req ID | Category | Requirement |
|--------|----------|-------------|
| NFR-01 | **Performance** | With the Mock LLM provider (no network I/O), individual agent execution shall complete in well under 1 second. With a real LLM provider, per-agent latency is bounded by that provider's own response time plus the orchestrator's retry policy (`max_retries`, default 3, exponential backoff from `retry_base_delay_seconds`, default 0.5s — see `src/shared/config.py`), not by this system's own processing. Actual measured values are recorded in `docs/project_report.md §7.2` once benchmarking is run. |
| NFR-02 | **Scalability** | The architecture shall support addition of new agent types without modifying the orchestrator core logic. |
| NFR-03 | **Reliability** | The system shall implement retry logic (max 3 attempts) with exponential backoff for transient API failures. |
| NFR-04 | **Maintainability** | All source code shall follow PEP 8 standards and include module-level and function-level docstrings. |
| NFR-05 | **Security** | API keys, tokens, and secrets shall be stored exclusively in `.env` files excluded via `.gitignore`. |
| NFR-06 | **Usability** | The system shall provide clear error messages and execution logs. |
| NFR-07 | **Portability** | The system shall run on Windows, macOS, and Linux without platform-specific modifications. |
| NFR-08 | **Testability** | All modules shall be testable in isolation using mock objects for external dependencies. |

---

## 4. Use Cases

### 4.1 Use Case Diagram

> *[Insert Use Case Diagram — source file at `diagrams/src_diagrams/use_case.puml` or `.drawio`]*
>
> *![Use Case Diagram](../diagrams/exports/use_case_diagram.png)*

### 4.2 Use Case Descriptions

#### UC-01: Submit Task for Execution

| Field | Description |
|---|---|
| **Use Case ID** | UC-01 |
| **Name** | Submit Task for Execution |
| **Actor(s)** | User |
| **Precondition** | System is initialised; API keys are configured in `.env`. |
| **Main Flow** | 1. User provides a task string to the Orchestrator. <br> 2. Orchestrator invokes the Planner Agent to decompose the task. <br> 3. Planner returns a list of sub-tasks. <br> 4. Orchestrator dispatches each sub-task to the Research Agent. <br> 5. Research Agent returns results for each sub-task. <br> 6. Orchestrator sends aggregated results to the Validator Agent. <br> 7. Validator confirms output quality. <br> 8. Orchestrator returns the final result to the user. |
| **Postcondition** | User receives the validated, aggregated result. |
| **Alternate Flow** | **A1:** If Planner fails → Orchestrator returns error with reason. <br> **A2:** If Validator rejects → Orchestrator retries or returns partial result. |
| **Exceptions** | API timeout, network failure, invalid input format. |

#### UC-02: Configure System Settings

| Field | Description |
|---|---|
| **Use Case ID** | UC-02 |
| **Name** | Configure System Settings |
| **Actor(s)** | Developer |
| **Precondition** | `.env.example` file exists in the repository root. |
| **Main Flow** | 1. Developer copies `.env.example` to `.env`. <br> 2. Developer fills in API keys and configuration values. <br> 3. System loads configuration on next startup via `config.py`. |
| **Postcondition** | System is configured and ready for task execution. |
| **Alternate Flow** | If `.env` is missing, system uses default values and logs a warning. |

#### UC-03: Submit and Poll a Task via the HTTP API

| Field | Description |
|---|---|
| **Use Case ID** | UC-03 |
| **Name** | Submit and Poll a Task via the HTTP API |
| **Actor(s)** | Developer / Researcher (HTTP client) |
| **Precondition** | The FastAPI app (`src/api/main.py`) is running; the SQLite database has been initialised. |
| **Main Flow** | 1. Client sends `POST /tasks` with `{"task": "..."}`. <br> 2. API creates a `TaskRecord` with `status="pending"`, returns it immediately (HTTP 201), and schedules the Orchestrator pipeline to run in the background. <br> 3. Client polls `GET /tasks/{id}` until `status` is `"success"`, `"partial"`, or `"error"`. <br> 4. Client reads the final `result`/`error` from the response. |
| **Postcondition** | The task's full outcome (result, error, retries used, step trace) is persisted and retrievable by id. |
| **Alternate Flow** | **A1:** Empty `task` string → HTTP 422 before any orchestrator run is scheduled. <br> **A2:** Unknown task id → HTTP 404. <br> **A3:** Orchestrator pipeline crashes unexpectedly → task record is marked `status="error"` rather than left stuck at `"pending"`. |

---

## 5. Hardware and Software Requirements

### 5.1 Hardware Requirements

| Component | Minimum Specification |
|-----------|----------------------|
| Processor | Intel Core i5 / AMD Ryzen 5 (or equivalent) |
| RAM | 8 GB |
| Disk Space | 5 GB free |
| Network | Broadband internet connection |

### 5.2 Software Requirements

| Component | Version / Specification |
|-----------|------------------------|
| Operating System | Windows 10+, macOS 12+, Ubuntu 20.04+ |
| Python | 3.10 or higher |
| pip | Latest stable |
| Git | 2.30+ |
| IDE (recommended) | VS Code with Python extension |
| CI/CD | GitHub Actions (configured in `.github/workflows/tests.yml`) |

### 5.3 Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | ≥ 2.0.0 | Data validation and schema enforcement |
| pydantic-settings | ≥ 2.0.0 | Environment-based configuration |
| python-dotenv | ≥ 1.0.0 | Load `.env` files |
| pytest | ≥ 7.4.0 | Test framework |
| pytest-cov | ≥ 4.1.0 | Code coverage reporting |
| black | ≥ 23.0.0 | Code formatting |
| flake8 | ≥ 6.1.0 | Linting |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [DD/MM/YYYY] | [Student Name 1] | Initial SRS draft |
| | | | |
