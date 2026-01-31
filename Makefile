# Makefile - helper targets for QA and quick dev guards
.PHONY: quality test-frontend build-frontend test-backend ci status monitor up down logs help

quality:
	@echo "Running full quality checks..."
	./scripts/run_quality_checks.sh all

ci:
	@echo "Running local CI checks for front-end"
	cd "frontend/kilo-react-frontend" && npm run ci-local

test-frontend:
	cd "frontend/kilo-react-frontend" && npm test -- --watchAll=false --silent

build-frontend:
	cd "frontend/kilo-react-frontend" && npm run build --silent

test-backend:
	pytest -q

# System monitoring and management targets
help:
	@echo "Kilo Guardian - Available Make Targets:"
	@echo ""
	@echo "Quality & Testing:"
	@echo "  make quality         - Run full quality checks"
	@echo "  make ci              - Run local CI checks for frontend"
	@echo "  make test-frontend   - Run frontend tests"
	@echo "  make test-backend    - Run backend tests"
	@echo "  make build-frontend  - Build frontend"
	@echo ""
	@echo "System Monitoring:"
	@echo "  make status          - Quick system status snapshot"
	@echo "  make monitor         - Live monitoring dashboard (Ctrl+C to exit)"
	@echo ""
	@echo "Docker Management:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - View logs for all services"
	@echo ""

status:
	@./scripts/check-status.sh

monitor:
	@./scripts/monitor-system.sh

up:
	@LIBRARY_ADMIN_KEY=test123 docker-compose -f infra/docker/docker-compose.yml up -d

down:
	@docker-compose -f infra/docker/docker-compose.yml down

logs:
	@docker-compose -f infra/docker/docker-compose.yml logs -f --tail=50
