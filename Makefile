# Common tasks. `make help` lists them.
.DEFAULT_GOAL := help
.PHONY: help install dev worker test lint format migrate up down logs e2e

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	pip install -r requirements.txt
	cd frontend && npm install

dev: ## Run the API with autoreload (tasks run inline)
	uvicorn src.api.main:app --reload

worker: ## Run an arq worker (needs QUEUE_BACKEND=redis and Redis)
	arq src.worker.main.WorkerSettings

migrate: ## Apply database migrations
	alembic upgrade head

test: ## Run backend and frontend tests
	pytest --cov=src
	cd frontend && npm test

lint: ## Lint and type-check everything
	ruff check .
	black --check .
	mypy src --ignore-missing-imports
	cd frontend && npx tsc --noEmit

format: ## Auto-format
	ruff check --fix .
	black .
	cd frontend && npx prettier --write "src/**/*.{ts,tsx}"

up: ## Build and start the full stack (docker compose)
	docker compose up --build -d

down: ## Stop the stack and remove volumes
	docker compose down -v

logs: ## Tail stack logs
	docker compose logs -f

e2e: ## Run Playwright end-to-end tests against the stack
	cd frontend && npx playwright test
