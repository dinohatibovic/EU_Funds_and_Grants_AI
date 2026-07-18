.PHONY: build up down logs dev test ai-test lint ingest clean

COMPOSE = docker compose -f infrastructure/docker-compose.yml

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f backend

# Lokalni razvoj bez Dockera (zahtijeva pip install -r requirements.txt)
dev:
	uvicorn backend.app.main:app --reload

test:
	pytest tests/backend_tests/ -v

ai-test:
	pytest tests/ai_pipeline_tests/ -v

lint:
	ruff check --select E9,F63,F7,F82 .

ingest:
	python3 ai_core/rag_pipeline/ingestion/ingest_local_grants.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
