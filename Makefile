.PHONY: help setup install clean test lint format docker-up docker-down docker-build migrate seed

help:
	@echo "Commodity ERP - Available Commands"
@echo "================================"
@echo "setup         - Initial project setup"
@echo "install       - Install all dependencies"
@echo "clean         - Clean build artifacts and caches"
@echo "test          - Run all tests"
@echo "lint          - Run linters"
@echo "format        - Format code"
@echo "docker-up     - Start Docker containers"
@echo "docker-down   - Stop Docker containers"
@echo "docker-build  - Build Docker images"
@echo "migrate       - Run database migrations"
@echo "seed          - Seed database with initial data"
@echo "dev-backend   - Run backend in development mode"
@echo "dev-frontend  - Run frontend in development mode"
@echo "dev-mobile    - Run mobile app"

setup:
	@echo "Setting up Commodity ERP..."
@cp .env.example .env
@echo "Created .env file"
@echo "Please update .env with your configuration"

install: install-backend install-frontend install-mobile

install-backend:
@echo "Installing backend dependencies..."
@cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt

install-frontend:
@echo "Installing frontend dependencies..."
@cd frontend && npm install

install-mobile:
@echo "Installing mobile dependencies..."
@cd mobile && npm install

clean:
@echo "Cleaning build artifacts..."
@find . -type d -name "__pycache__" -exec rm -rf {} +
@find . -type f -name "*.pyc" -delete
@find . -type d -name "node_modules" -exec rm -rf {} +
@find . -type d -name "dist" -exec rm -rf {} +
@find . -type d -name "build" -exec rm -rf {} +
@rm -rf logs/*.log

test: test-backend test-frontend test-mobile

test-backend:
@echo "Running backend tests..."
@cd backend && . venv/bin/activate && pytest

test-frontend:
@echo "Running frontend tests..."
@cd frontend && npm test

test-mobile:
@echo "Running mobile tests..."
@cd mobile && npm test

lint: lint-backend lint-frontend lint-mobile

lint-backend:
@echo "Linting backend..."
@cd backend && . venv/bin/activate && flake8 . && mypy .

lint-frontend:
@echo "Linting frontend..."
@cd frontend && npm run lint

lint-mobile:
@echo "Linting mobile..."
@cd mobile && npm run lint

format: format-backend format-frontend format-mobile

format-backend:
@echo "Formatting backend..."
@cd backend && . venv/bin/activate && black . && isort .

format-frontend:
@echo "Formatting frontend..."
@cd frontend && npm run format

format-mobile:
@echo "Formatting mobile..."
@cd mobile && npm run format

docker-up:
@echo "Starting Docker containers..."
@docker-compose up -d

docker-down:
@echo "Stopping Docker containers..."
@docker-compose down

docker-build:
@echo "Building Docker images..."
@docker-compose build

migrate:
@echo "Running database migrations..."
@cd backend && . venv/bin/activate && alembic upgrade head

seed:
@echo "Seeding database..."
@cd backend && . venv/bin/activate && python db/seeds/initial_data.py

dev-backend:
@echo "Starting backend in development mode..."
@cd backend && . venv/bin/activate && uvicorn app.main:app --reload

dev-frontend:
@echo "Starting frontend in development mode..."
@cd frontend && npm run dev

dev-mobile:
@echo "Starting mobile app..."
@cd mobile && npm start
