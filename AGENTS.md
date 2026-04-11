# Codex Project Instructions — Aegis

## Project

**Aegis** is an AI-Native DevSecOps Command Center. Open-source platform consolidating observability, reliability engineering, FinOps, and AI-powered incident management.

## Architecture

- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui (`apps/web/`)
- **API**: Go 1.26 + Fiber v2 (`apps/api/`)
- **AI Engine**: Python 3.14 + FastAPI + Claude API + MCP + LangGraph (`apps/ai-engine/`)
- **Databases**: PostgreSQL 16, ClickHouse, Redis 7
- **Monorepo**: pnpm + Turborepo

## Design System

- Dark-first terminal-inspired aesthetic
- Background: #1E1E2A (charcoal), Cards: #252535, Accent: #00FF88 (matrix green)
- Fonts: JetBrains Mono (code/headings), Inter (body), minimum 12px
- Metrics: 32px+ font size, charts: 300px+ height
- WCAG AA contrast (5.0:1+)
- 6 color presets: Matrix, Cyan, Amber, Violet, Red, Frost
- 3 density modes: Compact, Comfortable, Spacious

## Module Map

| Module | Path | Description |
|--------|------|-------------|
| Log Explorer | `apps/web/src/app/(dashboard)/logs/` | Log search + security logs |
| SLO Dashboard | `apps/web/src/app/(dashboard)/slo/` | SLO/SLI, error budgets |
| FinOps | `apps/web/src/app/(dashboard)/finops/` | Cloud cost, budgets, rightsizing |
| Incidents | `apps/web/src/app/(dashboard)/incidents/` | AI incident management |
| Security | `apps/web/src/app/(dashboard)/security/` | Vulnerability + compliance |
| IAM Audit | `apps/web/src/app/(dashboard)/iam/` | Roles, least privilege, CloudTrail |
| Deployments | `apps/web/src/app/(dashboard)/deployments/` | DORA metrics + deploy tracking |
| On-Call | `apps/web/src/app/(dashboard)/oncall/` | Schedules + runbooks |
| Services | `apps/web/src/app/(dashboard)/services/` | Service catalog |
| Settings | `apps/web/src/app/(dashboard)/settings/` | 5-tab settings page |
| Setup Wizard | `apps/web/src/app/(setup)/` | 6-step onboarding |

## Code Conventions

- TypeScript: ESLint + Prettier, strict mode
- Go: gofmt + golangci-lint
- Python: ruff format + lint
- Conventional Commits: `feat(module):`, `fix(module):`, `refactor(module):`
- Shared types in `packages/types/`
- Integration adapters in `packages/integrations/<provider>/`

## Engineering Guidelines

When making changes:
1. Components should be large and fill available space
2. All fonts minimum 12px, metrics 32px+, charts 300px+
3. Maintain WCAG AA contrast ratios
4. Use CSS variables from the theme system, never hardcode colors
5. Follow existing patterns in adjacent modules
6. TypeScript strict — no `any` types
7. Go error handling — always check and wrap errors
8. Python — type hints on all function signatures

## Safety Rules

- NEVER run `terraform apply`, `kubectl apply`, or provision infrastructure
- NEVER commit secrets, API keys, or credentials
- All Terraform/Helm/K8s files are code-only
- AI agent MCP WRITE tools require Slack approval

## Commands

```bash
pnpm dev          # Start frontend dev server
pnpm build        # Build all packages
pnpm lint         # Lint all packages
pnpm type-check   # Type check TypeScript
pnpm test         # Run tests
cd apps/api && go run .                    # API server
cd apps/ai-engine && uvicorn main:app      # AI engine
```
