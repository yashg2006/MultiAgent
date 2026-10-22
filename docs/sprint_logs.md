# Sprint Logs & Project Management Artifacts

## Multi-Agent AI System

---

| Field | Details |
|---|---|
| **Team Members** | Dhanika Bhat (Reg: 24BRS1356), Ayushi Singh (Reg: 24BRS1369), Yash Gharat (Reg: 24BRS1357) |
| **Faculty Guide** | Prof. _(faculty name — fill before submission)_ |
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

| Task | Dhanika Bhat | Ayushi Singh | Yash Gharat |
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
| R-06 | No shared local runtime; bugs only surface in CI | Medium | Medium | Small PRs; rich CI annotations; Mock provider for determinism | Mitigated |

---

## Sprint Logs

---

### Sprint 1 — Weeks 1–2: Project Setup & Requirements

| Field | Details |
|---|---|
| **Sprint Goal** | Establish project infrastructure and draft initial SRS. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**Meeting 1 — _(date)_**
| Field | Details |
|---|---|
| Attendees | Dhanika Bhat, Ayushi Singh, Yash Gharat |
| Duration | _(duration)_ |
| Agenda | Kick-off, project topic finalisation, repository setup |
| Discussion | [Key discussion points] |
| Decisions | [Decisions made — e.g., chose orchestrator-agent pattern, Python + Pydantic stack] |

**Action Items:**

| Item | Assigned To | Deadline | Status |
|------|-------------|----------|--------|
| Create GitHub repository with scaffolding | Dhanika Bhat | — | Done |
| Draft SRS Sections 1–2 | Ayushi Singh | — | Done |
| Research existing multi-agent systems for lit survey | Yash Gharat | — | Done |

**Sprint Retrospective:**
- **What went well:** [e.g., repo setup completed on day 1]
- **What could improve:** [e.g., need clearer task decomposition upfront]
- **Action for next sprint:** [e.g., use a shared task board]

---

### Sprint 2 — Weeks 3–4: Architecture Design

| Field | Details |
|---|---|
| **Sprint Goal** | Finalise architecture design and agent interface contracts. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**Meeting 2 — _(date)_**
| Field | Details |
|---|---|
| Attendees | Dhanika Bhat, Ayushi Singh, Yash Gharat |
| Duration | _(duration)_ |
| Agenda | Architecture review, schema finalisation, sprint planning |
| Discussion | [Key discussion points] |
| Decisions | [Decisions made] |

**Action Items:**

| Item | Assigned To | Deadline | Status |
|------|-------------|----------|--------|
| Create architecture diagram | Dhanika Bhat | — | Done |
| Define AgentRequest/AgentResponse schemas | Dhanika Bhat | — | Done |
| Complete SRS functional requirements | Ayushi Singh | — | Done |
| Draft use case diagrams | Yash Gharat | — | Done |

**Sprint Retrospective:**
- **What went well:** [Fill]
- **What could improve:** [Fill]
- **Action for next sprint:** [Fill]

---

### Sprint 3 — Weeks 5–7: Core Implementation

| Field | Details |
|---|---|
| **Sprint Goal** | Implement Orchestrator core and Research Agent. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**Meeting 3 — _(date)_**
| Field | Details |
|---|---|
| Attendees | [Names] |
| Duration | _(duration)_ |
| Agenda | [Agenda] |
| Discussion | [Discussion] |
| Decisions | [Decisions] |

**Action Items:**

| Item | Assigned To | Deadline | Status |
|------|-------------|----------|--------|
| Implement Orchestrator `run()` method | Dhanika Bhat | — | Done |
| Implement Research Agent `execute()` | Ayushi Singh | — | Done |
| Write unit tests for Orchestrator | Dhanika Bhat | — | Done |
| Write unit tests for Research Agent | Ayushi Singh | — | Done |

**Sprint Retrospective:**
- **What went well:** [Fill]
- **What could improve:** [Fill]
- **Action for next sprint:** [Fill]

---

### Sprint 4 — Weeks 8–10: Agent Implementation

| Field | Details |
|---|---|
| **Sprint Goal** | Implement Planner Agent and Validator Agent. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**[Meeting minutes template — same format as above]**

---

### Sprint 5 — Weeks 11–12: Integration Testing

| Field | Details |
|---|---|
| **Sprint Goal** | End-to-end integration testing and bug fixing. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**[Meeting minutes template — same format as above]**

---

### Sprint 6 — Weeks 13–14: System Testing & Documentation

| Field | Details |
|---|---|
| **Sprint Goal** | System testing, documentation completion, and report writing. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**[Meeting minutes template — same format as above]**

---

### Sprint 7 — Week 15: Final Submission

| Field | Details |
|---|---|
| **Sprint Goal** | Final submission, presentation preparation. |
| **Sprint Dates** | _(sprint dates — fill before submission)_ |

**[Meeting minutes template — same format as above]**

---

## Backlog (if using Agile)

| ID | User Story / Task | Priority | Sprint | Status |
|----|------------------|----------|--------|--------|
| BL-01 | As a user, I want to submit a task and receive results | High | Sprint 3 | Done |
| BL-02 | As a developer, I want shared schemas for agent communication | High | Sprint 2 | Done |
| BL-03 | As a user, I want the system to retry on API failures | Medium | Sprint 4 | Done |
| BL-04 | As a user, I want a live trace of each run and the ability to cancel it | Medium | Sprint 5 | Done |

---

## Burndown Tracking (if using Agile)

> Progress was tracked through the GitHub pull-request history (one PR per phase, A–F) and the CI status on each. A burndown chart can be generated from the issue/PR close dates if the rubric requires one.
>

Story points were not tracked numerically; the table below is left for the team
to fill if the rubric requires story-point velocity. Each sprint corresponds to
one build phase (A–F) delivered as a merged pull request.

| Sprint | Planned Story Points | Completed | Remaining |
|--------|---------------------|-----------|-----------|
| Sprint 1 | — | — | — |
| Sprint 2 | — | — | — |
| Sprint 3 | — | — | — |
| Sprint 4 | — | — | — |
| Sprint 5 | — | — | — |
| Sprint 6 | — | — | — |
| Sprint 7 | — | — | — |
