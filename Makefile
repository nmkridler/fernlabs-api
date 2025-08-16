.PHONY: help install run test clean migrate

help: ## Show this help message
	@echo "FernLabs API - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

run: ## Run the API server
	uvicorn fernlabs_api.app:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run database migrations
	python migrate_db.py

test: ## Run the test script
	python test_workflow.py

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

setup: install migrate ## Install dependencies and run migrations

dev: setup ## Setup development environment
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the API server"
	@echo "Run 'make test' to test the system"
