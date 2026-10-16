.DEFAULT_GOAL := help

# Backend defaults to APP_PORT from .env. Override either port at invocation time.
BACKEND_PORT ?=
FRONTEND_PORT ?= 5173
SERVICE ?= all
export BACKEND_PORT FRONTEND_PORT SERVICE

.PHONY: help setup start stop restart status logs logs-follow stop-apps db-start db-stop db-logs migrate test test-backend test-frontend test-tools test-postgres lint format build rag-check

help: ## Show available commands
	@python3 scripts/dev.py help

setup: ## Install dependencies and create .env only if missing
	@python3 scripts/dev.py setup

start: ## Start database, migrate, and start backend/frontend in the background
	@python3 scripts/dev.py start

stop: ## Stop managed apps and database; preserve database data
	@python3 scripts/dev.py stop

stop-apps: ## Stop managed backend/frontend and leave database running
	@python3 scripts/dev.py stop-apps

restart: ## Restart the managed local stack
	@python3 scripts/dev.py restart

status: ## Show process ownership, URLs, and database status
	@python3 scripts/dev.py status

logs: ## Show recent application logs (SERVICE=backend or frontend)
	@python3 scripts/dev.py logs

logs-follow: ## Follow application logs; Ctrl+C exits the viewer
	@python3 scripts/dev.py logs --follow

db-start: ## Start PostgreSQL and wait until healthy
	@python3 scripts/dev.py db-start

db-stop: ## Stop PostgreSQL without deleting its volume
	@python3 scripts/dev.py db-stop

db-logs: ## Follow PostgreSQL logs
	@python3 scripts/dev.py db-logs

migrate: ## Apply database migrations
	@cd backend && uv run --no-sync alembic upgrade head

test: test-backend test-frontend test-tools ## Run isolated backend, frontend, and service-control checks

test-backend: ## Run isolated backend tests (no live APIs)
	@cd backend && uv run --no-sync pytest -q

test-frontend: ## Run frontend checks
	@cd frontend && pnpm test

test-tools: ## Check process ownership and occupied-port protection
	@python3 -m unittest discover -s tests -p 'test_dev_commands.py' -v

test-postgres: ## Run PostgreSQL tests in a disposable local database
	@cd backend && PYTHONPATH=. uv run --no-sync python ../scripts/verify_postgres.py

lint: ## Check Python formatting and frontend lint
	@cd backend && uv run --no-sync black --check app tests ../scripts ../tests
	@cd frontend && pnpm lint

format: ## Format Python source and tests
	@cd backend && uv run --no-sync black app tests ../scripts ../tests

build: ## Type-check and build the frontend
	@cd frontend && pnpm build

rag-check: ## Run live Gemini acceptance checks (may incur API charges)
	@cd backend && PYTHONPATH=. uv run --no-sync python ../scripts/verify_rag.py --live --cases ../evaluation/rag-acceptance.json
