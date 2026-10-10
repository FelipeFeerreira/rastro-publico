.PHONY: help up down logs backend-dev frontend-dev migrate revision seed ingest test test-backend test-frontend lint fmt

help:
	@echo "Rastro Público - comandos disponíveis:"
	@echo "  make up              # sobe postgres + redis + api + web via docker compose"
	@echo "  make down            # derruba os containers"
	@echo "  make logs            # acompanha logs"
	@echo "  make migrate         # aplica migrações Alembic"
	@echo "  make revision m=...  # cria nova migração"
	@echo "  make ingest args=... # executa ingestão de dados (ex: args='pncp --data-inicial 2026-01-01 --data-final 2026-01-07')"
	@echo "  make test            # roda todos os testes"
	@echo "  make lint fmt        # qualidade de código"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

migrate:
	cd backend && alembic upgrade head

revision:
	cd backend && alembic revision --autogenerate -m "$(m)"

ingest:
	cd backend && python -m app.cli ingest $(args)

test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest -q

test-frontend:
	cd frontend && npm run test

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

fmt:
	cd backend && ruff format app tests
