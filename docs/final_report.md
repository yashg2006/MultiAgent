# Final Project Report

## Multi-Agent AI System

---

| Field | Details |
|---|---|
| **Project Title** | Multi-Agent AI System for [Problem Domain] |
| **Course Code** | _(course code — fill before submission)_ — Software Engineering |
| **Semester** | [Semester, Academic Year] |
| **Team Members** | Dhanika Bhat (24BRS1356), Ayushi Singh (24BRS1369), Yash Gharat (24BRS1357) |
| **Faculty Guide** | Prof. _(faculty name — fill before submission)_, School of Computer Science and Engineering (SCOPE), Vellore Institute of Technology, Chennai |
| **Submission Date** | _(date — fill before submission)_ |

---

## Executive Summary

> *(200–300 words)*
>
> [Summarise the complete project: problem addressed, approach taken (orchestrator-agent architecture), key technologies used, testing methodology, and final outcomes. This should be self-contained so a reader understands the entire project from this section alone.]

---

## Key Accomplishments

- Successfully designed and implemented a modular multi-agent AI system following the orchestrator-agent architectural pattern.
- Developed three specialised agents (Research, Planner, Validator) with standardised communication via Pydantic schemas.
- Achieved 98% backend line coverage through unit and integration testing with pytest (CI gate ≥ 80%), plus 34 frontend tests and 5 Playwright end-to-end scenarios.
- Established a comprehensive CI/CD pipeline using GitHub Actions: lint, type-check, tests with a coverage gate, Postgres/Redis integration tests, a container image scan (Trivy), dependency audits, and end-to-end tests against the Docker Compose stack.
- Maintained disciplined version control with 62 commits across feature branches, merged via pull requests into `develop` and `main`.
- Delivered the system as a containerised, multi-user, observable service with a benchmark comparing the multi-agent pipeline against a single-agent baseline.

---

## Challenges and Lessons Learned

### Technical Challenges
1. **Non-deterministic model output:** a real LLM returns varying text, so the Planner's JSON plan could not be assumed well-formed. Resolved with defensive parsing (`extract_json_object` + schema validation) and a single repair retry, and by keeping all tests on the Mock provider or recorded fixtures so they stay deterministic.
2. **Streaming live progress:** the first metrics/context middleware was built on Starlette's `BaseHTTPMiddleware`, which buffers responses and broke the Server-Sent-Events stream. Resolved by rewriting the middleware as plain ASGI so the SSE trace streams correctly.

### Process and Teamwork Lessons
1. **Early schema definition paid off:** fixing the `AgentRequest`/`AgentResponse` contract first let the three agents be built and tested independently without integration churn.
2. **CI as the source of truth:** with no shared local runtime, treating CI as the verification step — with rich annotations for coverage and failures — kept everyone confident that `develop` was always green.
3. **Documentation alongside code:** keeping the docs in the same PR as the behaviour change (a Definition-of-Done rule) was far easier than retrofitting documentation at the end.

---

## Individual Contributions

| Team Member | Key Contributions | Estimated Effort |
|-------------|------------------|-----------------|
| Dhanika Bhat (24BRS1356) | Orchestrator module, architecture design, integration testing, CI/CD setup | _(effort % — fill before submission)_ |
| Ayushi Singh (24BRS1369) | Research Agent, Planner Agent, SRS documentation | _(effort % — fill before submission)_ |
| Yash Gharat (24BRS1357) | Validator Agent, test plan, system testing, final report | _(effort % — fill before submission)_ |

---

## Final Metrics Summary

| Metric | Value |
|--------|-------|
| Total lines of source code | ~4,700 (3,036 backend Python + 1,632 frontend TS/TSX) |
| Total test cases | 204 (165 backend + 34 frontend + 5 Playwright E2E) |
| Code coverage | 98% backend lines (CI gate ≥ 80%) |
| Git commits | 62 |
| Sprints completed | 7 |
| Documents delivered | 6 (SRS, Architecture, Test Plan, Project Report, Final Report, Sprint Logs) |

---

## References

> *[Duplicate or reference the References section from `project_report.md`]*

See full reference list in the [Project Report](./project_report.md#10-references).

---

## Appendix

- Full project report: [`docs/project_report.md`](./project_report.md)
- SRS: [`docs/SRS.md`](./SRS.md)
- Architecture design: [`docs/architecture_design.md`](./architecture_design.md)
- Test plan: [`docs/test_plan.md`](./test_plan.md)
- Sprint logs: [`docs/sprint_logs.md`](./sprint_logs.md)
- GitHub repository: https://github.com/yashg2006/MultiAgent
