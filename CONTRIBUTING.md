# Contributing Guidelines

Welcome to the team project repository! Please follow these contribution guidelines.

## Branch Naming Conventions
Always create feature branches off of `main` (or `develop`). Use the following prefix convention:
- `feature/<short-description>`: For new features or agent capabilities (e.g., `feature/research-agent-search`).
- `bugfix/<short-description>`: For fixing broken logic or bugs (e.g., `bugfix/orchestrator-timeout`).
- `docs/<short-description>`: For updates to project documentation (e.g., `docs/update-srs`).
- `refactor/<short-description>`: For code refactoring without behavior changes.

## Commit Message Conventions
We follow clear, descriptive commit conventions:
- `<type>: <short sentence in imperative tone>`

### Examples:
- `feat: add research agent web search capability`
- `fix: resolve null pointer in orchestrator state`
- `docs: update SRS functional requirements`
- `test: add unit tests for validator agent`

## Pull Request Guidelines
1. Ensure all `pytest` test cases pass before opening a PR.
2. Request a code review from at least one team member.
3. Ensure no sensitive credentials or `.env` files are committed.
