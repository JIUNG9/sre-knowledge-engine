# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-03-05

### Added

- Security Dashboard with vulnerability scanning integration (Trivy, Snyk, Grype)
- Compliance tracking for CIS, SOC2, ISO27001 benchmarks
- RBAC audit view connected to Keycloak OIDC
- Deployment Tracker with DORA metrics (all four key metrics)
- Performance ratings (Elite/High/Medium/Low) per DORA metric
- Deployment timeline with success/failed/rollback status tracking
- Deploy frequency and lead time charts

## [0.7.0] - 2026-02-15

### Added

- Slack approval workflow for AI-powered auto-remediation
- Slack client with Block Kit message formatting (incident alerts, approval requests)
- Interactive approve/reject/info buttons per remediation step
- Webhook handler for Slack interactive message callbacks
- Request signature verification for webhook security
- Frontend Slack approval status component with step-by-step progress
- Resolution notification posted to channel after successful remediation
- Approval audit trail tracking

## [0.6.0] - 2026-01-28

### Added

- Claude API integration for AI-powered incident investigation
- LangGraph-based IncidentOrchestrator with multi-step investigation pipeline
- MCP server with tool execution, audit logging, and approval model
- RemediationAgent for context-aware fix proposals (kubectl, terraform, config, code)
- Token tracking service with per-investigation cost estimation
- AI investigation panel in incident detail (summary, RCA, confidence score)
- Terminal-style investigation chat showing tool calls and AI reasoning
- Remediation steps UI with approve/reject and risk level badges
- MCP tool badges showing which tools were used
- MCP management API (list tools, execute, audit log, stats)

## [0.5.0] - 2026-01-10

### Added

- Incident Management MVP with full lifecycle workflow
- Incident list with severity/status filtering and card/table view toggle
- Incident detail panel with chronological timeline visualization
- Create incident form with severity, service, and assignee selection
- Real-time alert feed sidebar with SigNoz/Datadog/Prometheus source badges
- Incident timeline events (acknowledge, status change, notes, escalate)
- Alert ingestion from Prometheus Alertmanager webhook format
- Alert deduplication via fingerprint matching
- Incident statistics (active counts by severity, MTTR, resolution rate)

## [0.4.0] - 2025-12-12

### Added

- FinOps Dashboard with real-time cloud cost tracking
- Cost overview: monthly spend, MoM change, provider breakdown
- Cost by service table with trend sparklines and sorting
- Cost anomaly detection with severity-based cards
- Budget tracker with projected end-of-month spend
- Kubernetes cost allocation by namespace with idle resource metrics
- Cost trend comparison chart (MoM, QoQ) with daily granularity
- FinOps API: summary, costs, trends, anomalies, budgets, K8s costs

## [0.3.0] - 2025-11-25

### Added

- SLO/SLI Dashboard with error budget visualization and burn rate tracking
- SLO overview grid with meeting/at-risk/breaching status indicators
- Error budget burn-down chart (Recharts area with color transitions)
- SLO detail view with burn rate trend and event annotations
- Create/edit SLO form with service, target, window, and SLI type selection
- Time window toggle (Weekly/Monthly/Quarterly/Annually)
- Service health grid with aggregate status and sparkline trends
- Full SLO CRUD API (list, get, create, update, delete)
- Error budget time series API for charting
- Service catalog API with health status

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
