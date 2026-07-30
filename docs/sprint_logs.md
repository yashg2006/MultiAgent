# Sprint Logs & Project Management Artifacts

## Multi-Agent AI System

---

| Field | Details |
|---|---|
| **Team Members** | [Student Name 1] (Reg: [XXXXXXXXX]), [Student Name 2] (Reg: [XXXXXXXXX]), [Student Name 3] (Reg: [XXXXXXXXX]) |
| **Faculty Guide** | Prof. [Faculty Name] |
| **Methodology** | [Agile (Scrum) / Waterfall — confirm with course handout] |

---

## Gantt Chart — Semester Timeline

```
Week    1  2  3  4  5  6  7  8  9  10 11 12 13 14 15
        ├──┤──┤──┤──┤──┤──┤──┤──┤──┤──┤──┤──┤──┤──┤──┤
Sprint 1 ████                                           Setup & SRS
Sprint 2       ████                                     Architecture
Sprint 3             ██████                              Core Impl.
Sprint 4                      ██████                     Agent Impl.
Sprint 5                               ████             Integration
Sprint 6                                     ████       System Test
Sprint 7                                           ██   Final Sub.
SRS Doc  ████████                                        
Arch Doc       ████████                                 
Test Plan            ████████████                        
Report                                     ████████████ 
```

---

## Task Allocation Matrix

| Task | [Student Name 1] | [Student Name 2] | [Student Name 3] |
|------|:-:|:-:|:-:|
| Repository setup & scaffolding | ✅ Lead | Support | Support |
| SRS document drafting | Support | ✅ Lead | Support |
| Architecture design | ✅ Lead | Support | Review |
| Orchestrator implementation | ✅ Lead | Support | — |
| Research Agent implementation | — | ✅ Lead | Support |
| Planner Agent implementation | Support | ✅ Lead | — |
| Validator Agent implementation | — | Support | ✅ Lead |
| Shared schemas & utilities | ✅ Lead | — | Support |
| Unit testing (per module) | Own module | Own module | Own module |
| Integration testing | ✅ Lead | Support | Support |
| System testing | Support | — | ✅ Lead |
| Test plan document | — | Support | ✅ Lead |
| Sprint logs / meeting minutes | Rotating | Rotating | Rotating |
| Final report | Support | Support | ✅ Lead |
| Presentation preparation | All | All | All |

---

## Risk Register

| Risk ID | Risk Description | Probability | Impact | Mitigation Strategy | Status |
|---------|-----------------|:-----------:|:------:|---------------------|--------|
| R-01 | LLM API rate limits or prolonged downtime | Medium | High | Implement retry with exponential backoff; cache responses; have a mock/fallback mode | Open |
| R-02 | Scope creep from adding agent features | High | Medium | Freeze scope after Sprint 2; use change request process for new features | Open |
| R-03 | Team member unavailability during mid-term exams | Medium | Medium | Front-load critical work in Sprints 1–3; maintain documentation so others can pick up tasks | Open |
| R-04 | Integration failures between agents (schema mismatches) | Medium | High | Define shared Pydantic schemas in Sprint 1; continuous integration testing from Sprint 3 | Open |
| R-05 | GitHub Actions CI pipeline configuration issues | Low | Low | Test workflow locally with `act`; keep workflow simple | Open |
| R-06 | [Placeholder risk] | [Prob] | [Impact] | [Mitigation] | Open |

---

## Sprint Logs

---

### Sprint 1 — Weeks 1–2: Project Setup & Requirements

| Field | Details |
|---|---|
| **Sprint Goal** | Establish project infrastructure and draft initial SRS. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**Meeting 1 — [DD/MM/YYYY]**
| Field | Details |
|---|---|
| Attendees | [Student Name 1], [Student Name 2], [Student Name 3] |
| Duration | [X] minutes |
| Agenda | Kick-off, project topic finalisation, repository setup |
| Discussion | [Key discussion points] |
| Decisions | [Decisions made — e.g., chose orchestrator-agent pattern, Python + Pydantic stack] |

**Action Items:**

| Item | Assigned To | Deadline | Status |
|------|-------------|----------|--------|
| Create GitHub repository with scaffolding | [Student Name 1] | [Date] | [Done/In Progress] |
| Draft SRS Sections 1–2 | [Student Name 2] | [Date] | [Done/In Progress] |
| Research existing multi-agent systems for lit survey | [Student Name 3] | [Date] | [Done/In Progress] |

**Sprint Retrospective:**
- **What went well:** [e.g., repo setup completed on day 1]
- **What could improve:** [e.g., need clearer task decomposition upfront]
- **Action for next sprint:** [e.g., use a shared task board]

---

### Sprint 2 — Weeks 3–4: Architecture Design

| Field | Details |
|---|---|
| **Sprint Goal** | Finalise architecture design and agent interface contracts. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**Meeting 2 — [DD/MM/YYYY]**
| Field | Details |
|---|---|
| Attendees | [Student Name 1], [Student Name 2], [Student Name 3] |
| Duration | [X] minutes |
| Agenda | Architecture review, schema finalisation, sprint planning |
| Discussion | [Key discussion points] |
| Decisions | [Decisions made] |

**Action Items:**

| Item | Assigned To | Deadline | Status |
|------|-------------|----------|--------|
| Create architecture diagram | [Student Name 1] | [Date] | [Done/In Progress] |
| Define AgentRequest/AgentResponse schemas | [Student Name 1] | [Date] | [Done/In Progress] |
| Complete SRS functional requirements | [Student Name 2] | [Date] | [Done/In Progress] |
| Draft use case diagrams | [Student Name 3] | [Date] | [Done/In Progress] |

**Sprint Retrospective:**
- **What went well:** [Fill]
- **What could improve:** [Fill]
- **Action for next sprint:** [Fill]

---

### Sprint 3 — Weeks 5–7: Core Implementation

| Field | Details |
|---|---|
| **Sprint Goal** | Implement Orchestrator core and Research Agent. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**Meeting 3 — [DD/MM/YYYY]**
| Field | Details |
|---|---|
| Attendees | [Names] |
| Duration | [X] minutes |
| Agenda | [Agenda] |
| Discussion | [Discussion] |
| Decisions | [Decisions] |

**Action Items:**

| Item | Assigned To | Deadline | Status |
|------|-------------|----------|--------|
| Implement Orchestrator `run()` method | [Student Name 1] | [Date] | [Status] |
| Implement Research Agent `execute()` | [Student Name 2] | [Date] | [Status] |
| Write unit tests for Orchestrator | [Student Name 1] | [Date] | [Status] |
| Write unit tests for Research Agent | [Student Name 2] | [Date] | [Status] |

**Sprint Retrospective:**
- **What went well:** [Fill]
- **What could improve:** [Fill]
- **Action for next sprint:** [Fill]

---

### Sprint 4 — Weeks 8–10: Agent Implementation

| Field | Details |
|---|---|
| **Sprint Goal** | Implement Planner Agent and Validator Agent. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**[Meeting minutes template — same format as above]**

---

### Sprint 5 — Weeks 11–12: Integration Testing

| Field | Details |
|---|---|
| **Sprint Goal** | End-to-end integration testing and bug fixing. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**[Meeting minutes template — same format as above]**

---

### Sprint 6 — Weeks 13–14: System Testing & Documentation

| Field | Details |
|---|---|
| **Sprint Goal** | System testing, documentation completion, and report writing. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**[Meeting minutes template — same format as above]**

---

### Sprint 7 — Week 15: Final Submission

| Field | Details |
|---|---|
| **Sprint Goal** | Final submission, presentation preparation. |
| **Sprint Dates** | [DD/MM/YYYY] — [DD/MM/YYYY] |

**[Meeting minutes template — same format as above]**

---

## Backlog (if using Agile)

| ID | User Story / Task | Priority | Sprint | Status |
|----|------------------|----------|--------|--------|
| BL-01 | As a user, I want to submit a task and receive results | High | Sprint 3 | [Status] |
| BL-02 | As a developer, I want shared schemas for agent communication | High | Sprint 2 | [Status] |
| BL-03 | As a user, I want the system to retry on API failures | Medium | Sprint 4 | [Status] |
| BL-04 | [Placeholder] | [Priority] | [Sprint] | [Status] |

---

## Burndown Tracking (if using Agile)

> *[Insert burndown chart image or data after each sprint]*
>
> *![Burndown Chart](../diagrams/exports/burndown_chart.png)*

| Sprint | Planned Story Points | Completed | Remaining |
|--------|---------------------|-----------|-----------|
| Sprint 1 | [X] | [Y] | [Z] |
| Sprint 2 | [X] | [Y] | [Z] |
| Sprint 3 | [X] | [Y] | [Z] |
| Sprint 4 | [X] | [Y] | [Z] |
| Sprint 5 | [X] | [Y] | [Z] |
| Sprint 6 | [X] | [Y] | [Z] |
| Sprint 7 | [X] | [Y] | [Z] |
