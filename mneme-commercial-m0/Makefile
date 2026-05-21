.PHONY: all up down seed reset demo test logs init-vault build classifier-test

all: up seed

# Bring everything up
up:
	docker compose up -d --build
	@echo "Waiting for postgres..."
	@until docker compose exec -T postgres pg_isready -U mneme >/dev/null 2>&1; do sleep 1; done
	@echo "Mneme is up. Console: http://localhost:5173"
	@echo "Gateway MCP:    http://localhost:8001"
	@echo "Console API:    http://localhost:8002"

# Initialize the vault as a real git repo (idempotent). Runs *inside* the
# gateway container so file ownership matches the runtime user.
init-vault:
	docker compose exec -T gateway python -m mneme_demo.seed.seed_vault

# Seed the vault (validates schemas + initializes git) and rebuild indices
seed: init-vault
	docker compose exec -T index-sync python -m mneme_index_sync.rebuild

# Reset everything (drop DB, reset vault repo to seed state)
reset:
	docker compose down -v
	rm -rf vault/.git
	$(MAKE) up
	$(MAKE) seed

# Run the 12-minute demo
demo:
	docker compose exec -T gateway python -m mneme_demo

# Run all tests
test:
	docker compose exec -T gateway pytest -x libs/ services/

# Pure-python classifier tests (no docker required)
classifier-test:
	cd libs/classifier && python -m pytest -x tests/

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build
