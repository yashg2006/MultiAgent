# Architecture Design Document

## Multi-Agent AI System

---

| Field | Details |
|---|---|
| **Document Version** | 1.0 |
| **Date** | _(date — fill before submission)_ |
| **Prepared By** | Dhanika Bhat, Ayushi Singh, Yash Gharat |
| **Faculty Guide** | Prof. _(faculty name — fill before submission)_ |

---

## 1. System Overview

The Multi-Agent AI System follows an orchestrator-agent architecture in which a central Orchestrator coordinates specialised autonomous agents to decompose, execute, and validate complex tasks. This design emphasises modularity, extensibility, and separation of concerns.

### 1.1 Use-Case Diagram

The actors are the end **User** (submits tasks and reviews runs through the SPA)
and the **Operator** (scrapes metrics and checks readiness for monitoring).
Source: [`diagrams/use_case.mmd`](../diagrams/use_case.mmd).

![Use-case diagram](assets/diagrams/use_case.png)

---

## 2. Architecture Diagram

The deployment/component architecture below is rendered from
[`diagrams/architecture.mmd`](../diagrams/architecture.mmd) by the `Diagrams`
CI workflow:

![Architecture diagram](assets/diagrams/architecture.png)

A simplified text view of the core request path:

```
┌────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                               │
│                        (CLI / API Call)                             │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                                │
│                                                                    │
│   ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐     │
│   │  Task Parser  │   │ Workflow      │   │ State Manager    │     │
│   │               │──▶│ Engine        │──▶│ & Error Handler  │     │
│   └──────────────┘   └───────────────┘   └──────────────────┘     │
│                                                                    │
└──────┬──────────────────┬──────────────────────┬───────────────────┘
       │                  │                      │
       │ AgentRequest     │ AgentRequest         │ AgentRequest
       ▼                  ▼                      ▼
┌──────────────┐   ┌──────────────┐   ┌────────────────────┐
│  RESEARCH    │   │  PLANNER     │   │   VALIDATOR        │
│  AGENT       │   │  AGENT       │   │   AGENT            │
│              │   │              │   │                    │
│  - Web/API   │   │  - Task      │   │  - Schema check   │
│    retrieval │   │    decomp.   │   │  - Quality rules  │
│  - Context   │   │  - Step      │   │  - Safety checks  │
│    building  │   │    ordering  │   │                    │
└──────┬───────┘   └──────┬───────┘   └────────┬───────────┘
       │                  │                      │
       │ AgentResponse    │ AgentResponse        │ AgentResponse
       ▼                  ▼                      ▼
┌────────────────────────────────────────────────────────────────────┐
│                     SHARED MODULE                                  │
│                                                                    │
│   ┌────────────┐   ┌────────────────┐   ┌──────────────────┐      │
│   │ schemas.py │   │   utils.py     │   │   config.py      │      │
│   │ (Pydantic) │   │ (Logging,      │   │ (Settings,       │      │
│   │            │   │  Retry logic)  │   │  Env Variables)  │      │
│   └────────────┘   └────────────────┘   └──────────────────┘      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │  EXTERNAL APIs   │
                   │  (LLM, Search,   │
                   │   Data Sources)  │
                   └──────────────────┘
```

---

## 3. Component Descriptions

### 3.1 Orchestrator (`src/orchestrator/`)

**Responsibility:** Central coordinator that receives user tasks, determines the execution plan, dispatches work to agents, and aggregates results.

**Sub-components:**
- **Task Parser** — Interprets raw user input and extracts intent, parameters, and constraints.
- **Workflow Engine** — Determines the sequence of agent invocations (sequential or parallel).
- **State Manager** — Tracks task progress, manages intermediate results, handles retries on failure.

### 3.2 Research Agent (`src/agents/research_agent/`)

**Responsibility:** Gathers information and context relevant to a sub-task.

**Input:** `AgentRequest` with a query prompt.
**Output:** `AgentResponse` with structured research findings.
**Dependencies:** External search APIs, document retrieval services, or LLM context generation.

### 3.3 Planner Agent (`src/agents/planner_agent/`)

**Responsibility:** Breaks down high-level objectives into a sequenced list of executable sub-tasks.

**Input:** `AgentRequest` with an objective description.
**Output:** `AgentResponse` containing an ordered list of sub-tasks with descriptions.
**Dependencies:** LLM API for task decomposition reasoning.

### 3.4 Validator Agent (`src/agents/validator_agent/`)

**Responsibility:** Reviews and validates outputs for correctness, completeness, and compliance with quality constraints.

**Input:** `AgentRequest` with result data to validate.
**Output:** `AgentResponse` with a boolean validation status and optional failure reasons.
**Dependencies:** Schema validation (Pydantic), custom rule checks.

### 3.5 Shared Module (`src/shared/`)

**Responsibility:** Cross-cutting utilities and data contracts used by all components.

- **`schemas.py`** — `AgentRequest` and `AgentResponse` Pydantic models defining the standard inter-agent communication contract.
- **`utils.py`** — Centralised logging configuration, retry helpers, and string/data formatting utilities.
- **`config.py`** — Application settings loaded from `.env` via `pydantic-settings`.

---

## 4. Sequence Diagram — Standard Task Execution

Research sub-tasks that do not depend on one another run in parallel, one
dependency level at a time; a failed validation retries up to `max_retries`
before a partial result is returned. Source:
[`diagrams/sequence.mmd`](../diagrams/sequence.mmd).

![Sequence diagram](assets/diagrams/sequence.png)

```mermaid
sequenceDiagram
    participant U as User (SPA)
    participant A as API
    participant Q as Redis
    participant W as Worker / Orchestrator
    participant P as Planner
    participant R as Research (pool)
    participant V as Validator

    U->>A: POST /tasks {task}
    A->>Q: enqueue job
    A-->>U: 201 {id, status=pending}
    U->>A: GET /tasks/{id}/events (SSE)
    Q->>W: deliver job
    W->>P: AgentRequest (plan)
    P-->>W: sub-tasks + depends_on
    loop Each dependency level
        par Independent sub-tasks in parallel
            W->>R: AgentRequest (query)
            R-->>W: findings (+usage)
        end
    end
    W->>V: AgentRequest (rules + judge)
    V-->>W: pass/fail + score
    alt score >= threshold and rules pass
        W-->>A: success + result
    else fail and retries left
        W->>R: re-run failed sub-tasks
    else retries exhausted
        W-->>A: partial result + errors
    end
    A-->>U: SSE step events, then final status + result
```

---

## 5. Activity Diagram — Task Processing Flow

Source: [`diagrams/activity.mmd`](../diagrams/activity.mmd).

![Activity diagram](assets/diagrams/activity.png)

**Flow Description:**
1. **Start** → Receive user task
2. Parse and validate input → [Invalid? → Return error] → [Valid? → Continue]
3. Invoke Planner Agent → Receive execution plan
4. For each sub-task in plan → Invoke Research Agent → Collect results
5. Aggregate results → Invoke Validator Agent
6. [Validation passed?] → Return final output → **End**
7. [Validation failed?] → [Retry limit reached?] → Return error → **End**
8. [Retry available?] → Re-execute failed sub-tasks → Return to step 4

---

## 6. Data Flow Diagrams

### 6.1 DFD Level 0 (Context Diagram)

Source: [`diagrams/dfd_level0.mmd`](../diagrams/dfd_level0.mmd).

![DFD Level 0](assets/diagrams/dfd_level0.png)

**Entities and Flows:**

| External Entity | Data In | Data Out |
|-----------------|---------|----------|
| User | Task string | Final result / Error message |
| LLM API | API responses | API requests (prompts) |

### 6.2 DFD Level 1

Source: [`diagrams/dfd_level1.mmd`](../diagrams/dfd_level1.mmd).

![DFD Level 1](assets/diagrams/dfd_level1.png)

**Processes:**

| Process | Input | Output | Data Store |
|---------|-------|--------|------------|
| P1: Task Parsing | Raw task string | Parsed task object | — |
| P2: Planning | Parsed task | Sub-task list | — |
| P3: Research | Sub-task query | Research results | Intermediate results |
| P4: Validation | Aggregated results | Validation status | — |

---

## 7. Class Diagram

Every agent implements the abstract `Agent` contract and talks to models only
through `Agent.call_llm()`; the Orchestrator holds its agents in a dict and
needs no change to accept a new one (NFR-02). Source:
[`diagrams/class.mmd`](../diagrams/class.mmd).

![Class diagram](assets/diagrams/class.png)

```mermaid
classDiagram
    class Agent {
        <<abstract>>
        +str name
        +call_llm(prompt, system) tuple~AgentResponse, LLMUsage~
        +execute(request: AgentRequest)* AgentResponse
    }
    class PlannerAgent {
        +execute(request) AgentResponse
    }
    class ResearchAgent {
        -SearchTool search
        +execute(request) AgentResponse
    }
    class ValidatorAgent {
        -float threshold
        +execute(request) AgentResponse
        +validate_with_usage(results, objective) tuple
    }
    class Orchestrator {
        -dict~str,Agent~ agents
        -int max_retries
        +run(task, on_step, is_cancelled) RunResult
        -_run_level(level, context) list
        -_dispatch(agent_key, request) tuple
    }
    class AgentRequest {
        +str objective
        +dict payload
    }
    class AgentResponse {
        +str status
        +dict data
        +LLMUsage usage
    }
    class LLMUsage {
        +int calls
        +int input_tokens
        +int output_tokens
        +float cost_usd
        +__add__(other) LLMUsage
    }
    class RunResult {
        +str status
        +dict result
        +int retries_used
        +LLMUsage usage
    }

    Agent <|-- PlannerAgent
    Agent <|-- ResearchAgent
    Agent <|-- ValidatorAgent
    Orchestrator o-- Agent
    Orchestrator ..> RunResult
    Agent ..> AgentRequest
    Agent ..> AgentResponse
    AgentResponse o-- LLMUsage
    RunResult o-- LLMUsage
```

---

## 8. Design Decisions and Rationale

| Decision | Rationale |
|----------|-----------|
| Orchestrator-Agent pattern over monolithic design | Enables independent development and testing of each agent; supports adding new agents without core changes. |
| Pydantic schemas for inter-agent communication | Enforces type safety and data validation at boundaries; auto-generates documentation. |
| Python as primary language | Strong AI/ML ecosystem; team familiarity; rapid prototyping. |
| Environment-based configuration (`.env`) | Separates secrets from code; follows 12-factor app principles. |
| pytest for testing | Industry standard; rich plugin ecosystem; integrates with GitHub Actions. |
| Hand-written orchestrator instead of LangGraph | The pipeline is a fixed sequence (plan → research levels → validate → retry), which ~200 lines of plain Python express directly and test exhaustively (98% coverage), including retries, cancellation and parallel levels. LangGraph would add a large dependency and a second state model without enabling anything the project needs; it remains an option if the flow becomes a general graph. |
| All model calls through one resilient path | `generate_with_resilience` applies retries (transient errors only), a shared circuit breaker, timeouts, and usage/cost accounting in one place, so every agent gets them and none can bypass them. |
| Mock provider as the default | Tests, CI and demos run offline, deterministically, at no cost; a real model is opt-in via `LLM_PROVIDER`. |

---

## 9. Extensibility Points

The architecture is designed for easy extension:

1. **New Agent Types:** Create a new subfolder under `src/agents/`, implement the agent class with `AgentRequest`/`AgentResponse` contracts, and register it with the Orchestrator.
2. **New Data Sources:** Add API wrappers or connectors in the Research Agent or as new shared utilities.
3. **Execution Strategies:** The Workflow Engine can be extended to support parallel execution, conditional branching, or human-in-the-loop steps.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | _(date — fill before submission)_ | Dhanika Bhat | Initial architecture design |
| | | | |
