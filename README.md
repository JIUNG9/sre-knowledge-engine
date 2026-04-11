<div align="center">

# Aegis

### AI-Native DevSecOps Command Center

[![CI](https://github.com/JIUNG9/aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/JIUNG9/aegis/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/JIUNG9/aegis?label=v3.0.0)](https://github.com/JIUNG9/aegis/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Go Report Card](https://goreportcard.com/badge/github.com/JIUNG9/aegis)](https://goreportcard.com/report/github.com/JIUNG9/aegis)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000?logo=next.js)](https://nextjs.org/)
[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org/)

**Consolidate observability, reliability engineering, FinOps, security, and AI-powered incident management into a single pane of glass.**

[Documentation](https://aegis-devsecops.dev/docs) | [Demo](https://demo.aegis-devsecops.dev) | [Discord](https://discord.gg/aegis) | [Blog](https://medium.com/@junegu)

</div>

---

## What is Aegis?

Aegis is an open-source DevSecOps platform that replaces the fragmented tooling (SigNoz, Datadog, Grafana, Confluence, JIRA, Slack, PagerDuty) that most SRE teams juggle. It provides a unified command center with AI-powered incident management via Claude API and MCP (Model Context Protocol).

**v3.0** brings AI token management with three intelligence modes, multi-cloud account management, IAM/RBAC administration, team settings, and full internationalization (English + Korean).

### Screenshots

> **SLO Dashboard** — Service-level objectives with error budget burn rates, team targets, and weekly/monthly/annual views.
>
> **FinOps** — Cloud cost breakdown by service, provider, and Kubernetes namespace with anomaly detection and rightsizing recommendations.
>
> **Incidents** — AI-powered incident timeline with root cause analysis, auto-remediation proposals, and Slack approval workflows.
>
> **Settings / AI & Tokens** — Three-mode AI engine selection (Eco / Standard / Deep Analysis), budget guardrails, and usage analytics.

---

## Core Modules

| # | Module | Route | Description |
|---|--------|-------|-------------|
| 1 | **Log Explorer** | `/logs` | Unified application + security log search powered by ClickHouse |
| 2 | **SLO/SLI Dashboard** | `/slo` | Error budgets, burn rate alerts, team targets, weekly/monthly/annual views |
| 3 | **FinOps** | `/finops` | Cloud cost tracking, K8s cost allocation, rightsizing, anomaly detection |
| 4 | **Incident Management** | `/incidents` | AI-powered investigation, root cause analysis, auto-remediation |
| 5 | **Security Dashboard** | `/security` | Vulnerability scanning, RBAC audit, compliance tracking |
| 6 | **Deployment Tracker** | `/deployments` | DORA metrics, deployment timeline, change failure rate |
| 7 | **On-Call & Runbooks** | `/oncall` | Rotation schedules, escalation policies, AI runbook assistant |
| 8 | **Service Catalog** | `/services` | Service registry, dependency maps, health scorecards |
| 9 | **IAM & Access** | `/iam` | Identity management, role-based access control, audit logs |
| 10 | **Cloud Accounts** | `/accounts` | Multi-cloud account management (AWS, GCP, Azure, a regional cloud) |
| 11 | **Settings** | `/settings` | General config, integrations, AI & tokens, team management |

---

## AI-Powered Features

Aegis ships with three AI intelligence modes, each backed by a different Claude model:

| Mode | Model | Input / Output | Latency | Best For |
|------|-------|---------------|---------|----------|
| **Eco** | Haiku 4.5 | $1 / $5 per 1M tokens | <2s | Monitoring, status checks |
| **Standard** | Sonnet 4.6 | $3 / $15 per 1M tokens | ~5s | Investigations, analysis |
| **Deep Analysis** | Opus 4.6 | $5 / $25 per 1M tokens | ~15s | Initial setup, critical incidents |

### Token Management

- **Budget guardrails** — Set monthly spend caps with auto-downgrade to Eco mode at configurable thresholds
- **Notification thresholds** — Alerts at 50%, 80%, and 100% of budget
- **Per-operation cost confirmation** — See estimated token cost before every AI action
- **Usage analytics** — 30-day spend charts, breakdown by module and mode
- **Mode toggle everywhere** — Switch modes from Settings or directly in the AI Assistant panel

### AI Incident Response Pipeline

```
Alert Triggered --> Aegis Ingests --> AI Investigates --> Proposes Fix --> Slack Approval --> Auto-Remediation --> Verification
```

When a critical alert fires, Aegis uses Claude API with MCP to:
1. Query your logs, metrics, and traces automatically
2. Analyze root cause across your entire stack
3. Propose a specific remediation (kubectl rollback, Terraform apply, config change)
4. Post to Slack with an approval workflow
5. Execute the fix on approval and verify resolution

**Cost: ~$0.15 per incident investigation** using Claude Sonnet 4.6 with prompt caching.

---

## Architecture

```
                              +-------------------+
                              |    Load Balancer   |
                              +--------+----------+
                                       |
              +------------------------+------------------------+
              |                        |                        |
    +---------v----------+   +---------v----------+   +---------v----------+
    |     Frontend       |   |     API Layer      |   |     AI Engine      |
    |   Next.js 16       |   |   Go + Fiber       |   |  Python + FastAPI  |
    |   React 19         |   |   REST + WebSocket  |   |  Claude API + MCP  |
    |   Tailwind CSS v4  |   |   JWT + OIDC Auth   |   |  LangGraph         |
    |   shadcn/ui        |   |   19 API Routes     |   |  Vector DB         |
    |   :3000            |   |   :8080             |   |  :8000             |
    +--------------------+   +---------+----------+   +---------+----------+
                                       |                        |
              +------------------------+------------------------+
              |              |              |              |
    +---------v--+ +---------v--+ +--------v---+ +--------v---+
    | PostgreSQL | | ClickHouse | |   Redis    | |     S3     |
    |    16      | | (logs/     | |   7        | | (artifacts)|
    |            | |  metrics)  | | (cache/    | |            |
    |            | |            | |  pubsub)   | |            |
    +------------+ +------------+ +------------+ +------------+
```

---

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/JIUNG9/aegis.git
cd aegis
cp .env.example .env
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Development

```bash
# Prerequisites: Node.js 20+, Go 1.22+, Python 3.12+, pnpm 9+

# Install dependencies
pnpm install

# Start all services in dev mode
pnpm dev

# Or start individually
cd apps/web && pnpm dev                         # Frontend — http://localhost:3000
cd apps/api && go run .                         # API      — http://localhost:8080
cd apps/ai-engine && uvicorn main:app --reload  # AI       — http://localhost:8000
```

### Build

```bash
pnpm build        # Build all packages
pnpm lint         # Lint all packages
pnpm type-check   # Type check all TypeScript
pnpm test         # Run all tests
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript 5, Tailwind CSS v4, shadcn/ui, Recharts, Zustand |
| API | Go 1.22+, Fiber, JWT/OIDC, OpenAPI 3.1 |
| AI Engine | Python 3.12+, FastAPI, Claude API (Haiku/Sonnet/Opus), MCP, LangGraph |
| Databases | PostgreSQL 16, ClickHouse (logs/metrics), Redis 7 (cache/pubsub) |
| Monorepo | pnpm 9, Turborepo |
| Deployment | Docker, Kubernetes (Helm), Terraform |
| CI/CD | GitHub Actions, Conventional Commits |
| Observability | OpenTelemetry, SigNoz |
| Design System | Dark-first terminal aesthetic, JetBrains Mono + Inter, 6 color presets, 3 density modes |

---

## Integrations

Aegis connects to your existing stack via a plugin system:

| Category | Providers |
|----------|-----------|
| **Observability** | SigNoz, Datadog, Prometheus, Grafana, CloudWatch |
| **Incident** | PagerDuty, Opsgenie, Slack, Microsoft Teams |
| **Ticketing** | JIRA, Linear, GitHub Issues |
| **Cloud** | AWS, GCP, Azure, a regional cloud |
| **Cost** | OpenCost, Kubecost, AWS Cost Explorer |
| **Security** | Trivy, Snyk, Grype |
| **CI/CD** | GitHub Actions, CircleCI, ArgoCD |
| **Source Control** | GitHub, GitLab, Bitbucket |

---

## Multi-Cloud Support

Aegis manages resources across multiple cloud providers and accounts:

- **AWS** — EC2, EKS, RDS, Lambda, S3, Cost Explorer, IAM
- **GCP** — GKE, Cloud Run, Cloud SQL, BigQuery, Billing
- **Azure** — AKS, App Service, Azure SQL, Cost Management
- **a regional cloud** (a regional cloud) — Server, Kubernetes Service, Cloud DB

Each account is configured with read-only IAM roles. Aegis never provisions or modifies infrastructure — it observes, analyzes, and recommends.

---

## Internationalization (i18n)

Aegis supports multiple languages out of the box:

- **English** (default)
- **Korean** (한국어)

Language can be switched per-user in Settings > General > Default Language.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork the repo, create a branch, make changes, submit a PR
git checkout -b feat/my-feature
# ... make changes ...
git commit -m "feat(module): add my feature"
git push origin feat/my-feature
```

### Branch Naming

```
feat/     — New features
fix/      — Bug fixes
docs/     — Documentation
refactor/ — Code refactoring
perf/     — Performance improvements
test/     — Tests
ci/       — CI/CD changes
chore/    — Maintenance
```

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with care by [June Gu](https://github.com/JIUNG9) | SRE at [acme-corp](https://example.com) (a large tech company)

</div>
