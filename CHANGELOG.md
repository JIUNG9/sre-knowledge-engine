# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-08

### Added

- Log Explorer page with full-text search, level/service filtering, and time range selection
- Real-time log streaming via WebSocket with live tail toggle
- Security log view with pre-filtered categories (auth failures, privilege escalation, network anomalies)
- ClickHouse storage layer with tokenbf_v1 bloom filter index for fast text search
- Log ingestion API endpoint with batch insert support
- WebSocket endpoint for concurrent live log streaming
- AI-powered log summarization and anomaly detection endpoints
- Natural language to ClickHouse query translation
- Log statistics bar (total, errors, warnings, rate)
- Saved queries with team sharing
- Mock log data generator with 100+ realistic entries
- ADR-005: Log Explorer Architecture

## [0.1.0] - 2025-10-20

### Added

- Initial project scaffolding with pnpm + Turborepo monorepo
- Next.js 16 frontend with shadcn/ui and Tailwind CSS v4
- Terminal-inspired dark-first design system (JetBrains Mono, matrix green accent)
- Go + Fiber API gateway with health check and route scaffolding
- Python FastAPI AI engine with MCP tool definitions
- Collapsible sidebar navigation with all 8 module placeholders
- Docker Compose for local development (PostgreSQL, Redis, ClickHouse)
- GitHub Actions CI pipeline (lint, type-check, build)
- Project documentation (README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT)
- Architecture Decision Records (ADR-001 through ADR-004)
- 10 AI agent role definitions for development workflow
