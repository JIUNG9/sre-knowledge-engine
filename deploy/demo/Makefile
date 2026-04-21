# ────────────────────────────────────────────────────────────────
#  Aegis Layer 0.8 — Demo Mode Makefile
# ────────────────────────────────────────────────────────────────
SHELL := /bin/bash
COMPOSE := docker compose -f docker-compose.demo.yml --env-file .env.demo
SEED_PY := python3

.PHONY: help demo demo-up demo-down demo-seed demo-logs demo-reset demo-test demo-ollama

help:
	@echo "Aegis Demo Mode targets:"
	@echo "  make demo         — boot full stack + seed data (default)"
	@echo "  make demo-up      — boot stack only (no seeding)"
	@echo "  make demo-down    — stop stack (data preserved)"
	@echo "  make demo-seed    — (re)run all seed scripts"
	@echo "  make demo-logs    — tail logs for all services"
	@echo "  make demo-reset   — stop + wipe all demo volumes"
	@echo "  make demo-test    — run smoke tests"
	@echo "  make demo-ollama  — boot stack with local LLM profile"

demo: demo-up demo-seed
	@echo ""
	@echo "═════════════════════════════════════════════════════"
	@echo "  Aegis Demo is ready!"
	@echo ""
	@echo "  Aegis UI         http://localhost:3000"
	@echo "  SigNoz UI        http://localhost:3301"
	@echo "  OTel Demo Shop   http://localhost:8080"
	@echo "  Aegis API docs   http://localhost:8000/docs"
	@echo "  Confluence mock  http://localhost:8090/rest/api/content"
	@echo "  LocalStack       http://localhost:4566/_localstack/health"
	@echo ""
	@echo "  Stop:    make demo-down"
	@echo "  Reset:   make demo-reset"
	@echo "═════════════════════════════════════════════════════"

demo-up:
	$(COMPOSE) up -d --remove-orphans
	@echo "[demo] waiting for services to become healthy..."
	@sleep 20

demo-ollama:
	$(COMPOSE) --profile ollama up -d --remove-orphans

demo-down:
	$(COMPOSE) down

demo-seed:
	@echo "[demo] seeding..."
	-$(SEED_PY) seed/seed_confluence.py --url http://localhost:8090
	-$(SEED_PY) seed/seed_localstack.py --endpoint http://localhost:4566
	-$(SEED_PY) seed/seed_incidents.py  --api http://localhost:8000 --count 48
	-$(SEED_PY) seed/seed_honeytokens.py --vault /tmp/aegis-demo-vault

demo-logs:
	$(COMPOSE) logs -f --tail=100

demo-reset:
	$(COMPOSE) down -v --remove-orphans
	@echo "[demo] all volumes wiped."

demo-test:
	$(SEED_PY) tests/smoke_test.py
