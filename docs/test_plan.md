# Test Plan

## 1. Objectives
Define test strategies for unit testing individual agents and integration testing the multi-agent pipeline.

## 2. Test Scope
- **Unit Testing:** Fast, mock-based unit tests for shared utilities, schemas, and individual agent logic.
- **Integration Testing:** End-to-end pipeline execution with mocked LLM responses and integration checks.

## 3. Test Tools & Frameworks
- `pytest` for test runner and assertions.
- `unittest.mock` / `pytest-mock` for mocking LLM calls and network operations.
