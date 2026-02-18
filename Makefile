.PHONY: install run dev test lint clean migrate migration migrate-down reset-db

install:
	poetry install

run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	poetry run pytest

test-integration:
	poetry run pytest -m integration

lint:
	poetry run ruff check .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

db-migrate:
	poetry run alembic upgrade head

db-generate:
	@read -p "Migration message: " msg; \
	poetry run alembic revision --autogenerate -m "$$msg"

db-migrate-down:
	poetry run alembic downgrade -1

db-seed:
	poetry run python -m app.db.seed

db-reset:
	@cd .. && \
		([ -f .env ] && set -a && . ./.env && set +a); \
		echo "Stopping Postgres and removing volume..." && \
		docker compose down -v && \
		echo "Starting Postgres..." && \
		docker compose up -d db && \
		echo "Waiting for Postgres to be ready..." && \
		until docker compose exec -T db pg_isready -U "$${DB_USER:-myuser}" -d "$${DB_NAME:-mydatabase}" 2>/dev/null; do sleep 1; done
