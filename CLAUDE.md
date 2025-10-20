# CLAUDE.md — Aegis Project

## Project Overview

**Aegis** is an AI-Native DevSecOps Command Center — an open-source platform that consolidates observability, reliability engineering, FinOps, and AI-powered incident management.

## Architecture

- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui (`apps/web/`)
- **API**: Go + Fiber (`apps/api/`)
- **AI Engine**: Python + FastAPI + Claude API + MCP (`apps/ai-engine/`)
- **Databases**: PostgreSQL 16, ClickHouse, Redis 7
- **Monorepo**: pnpm + Turborepo

## Key Conventions

### Git
- Conventional Commits: `feat(module): description`, `fix(module): description`
- Branch naming: `feat/`, `fix/`, `docs/`, `refactor/`, `perf/`, `test/`, `ci/`, `chore/`
- GitHub Flow with release branches

### Code Style
- TypeScript: ESLint + Prettier
- Go: gofmt + golangci-lint
- Python: ruff format + lint

### Design System
- Dark-first terminal-inspired aesthetic
- Typography: JetBrains Mono (code/headings), Inter (body)
- Primary accent: #00FF88 (matrix green)
- Background: #0A0A0F
- 6 color presets: Matrix, Cyan, Amber, Violet, Red, Frost
- 3 density modes: Compact, Comfortable, Spacious

## Module Structure

| Module | Location | Description |
|--------|----------|-------------|
| Log Explorer | `apps/web/src/app/(dashboard)/logs/` | Application + security log search |
| SLO Dashboard | `apps/web/src/app/(dashboard)/slo/` | SLO/SLI, error budgets |
| FinOps | `apps/web/src/app/(dashboard)/finops/` | Cloud cost management |
| Incidents | `apps/web/src/app/(dashboard)/incidents/` | AI-powered incident management |
| Security | `apps/web/src/app/(dashboard)/security/` | Vulnerability + compliance |
| Deployments | `apps/web/src/app/(dashboard)/deployments/` | DORA metrics + deploy tracking |
| On-Call | `apps/web/src/app/(dashboard)/oncall/` | Schedules + runbooks |
| Services | `apps/web/src/app/(dashboard)/services/` | Service catalog |

## Commands

```bash
pnpm dev          # Start all services in dev mode
pnpm build        # Build all packages
pnpm lint         # Lint all packages
pnpm type-check   # Type check all TypeScript
pnpm test         # Run all tests
```

## Important Rules

- NEVER run `terraform apply`, `kubectl apply`, or any infrastructure-provisioning commands
- All Terraform/Helm/K8s files are code-only — review before any provisioning
- AI agent MCP tools: READ tools are safe, WRITE tools require Slack approval, BLOCKED tools are never automated
- Shared types go in `packages/types/`
- Integration adapters go in `packages/integrations/<provider>/`
