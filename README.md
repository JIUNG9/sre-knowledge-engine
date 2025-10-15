<div align="center">

# Aegis

### AI-Native DevSecOps Command Center

[![CI](https://github.com/JIUNG9/aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/JIUNG9/aegis/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/JIUNG9/aegis)](https://github.com/JIUNG9/aegis/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Go Report Card](https://goreportcard.com/badge/github.com/JIUNG9/aegis)](https://goreportcard.com/report/github.com/JIUNG9/aegis)

**Consolidate observability, reliability engineering, FinOps, and AI-powered incident management into a single pane of glass.**

[Documentation](https://aegis-devsecops.dev/docs) | [Demo](https://demo.aegis-devsecops.dev) | [Discord](https://discord.gg/aegis) | [Blog](https://medium.com/@junegu)

</div>

---

## What is Aegis?

Aegis is an open-source DevSecOps platform that replaces the fragmented tooling (SigNoz, Datadog, Grafana, Confluence, JIRA, Slack) that most SRE teams juggle. It provides a unified command center with AI-powered incident management via Claude API.

### Core Modules

| Module | Description |
|--------|-------------|
| **Log Explorer** | Unified application + security log search powered by ClickHouse |
| **SLO/SLI Dashboard** | Error budgets, burn rate alerts, weekly/monthly/annual views |
| **FinOps** | Cloud cost tracking, K8s cost allocation, anomaly detection |
| **Incident Management** | AI-powered investigation, root cause analysis, auto-remediation |
| **Security Dashboard** | Vulnerability scanning, RBAC audit, compliance tracking |
| **Deployment Tracker** | DORA metrics, deployment timeline, change failure rate |
| **On-Call & Runbooks** | Rotation schedules, escalation policies, AI runbook assistant |
| **Service Catalog** | Service registry, dependency maps, health scorecards |

### Key Differentiator: AI-Powered Incident Response

```
Alert Triggered → Aegis Ingests → AI Investigates → Proposes Fix → Slack Approval → Auto-Remediation → Verification
```

When a critical alert fires, Aegis uses Claude API with MCP (Model Context Protocol) to:
1. Query your logs, metrics, and traces automatically
2. Analyze root cause across your entire stack
3. Propose a specific remediation (kubectl rollback, Terraform apply, config change)
4. Post to Slack with an approval workflow
5. Execute the fix on approval and verify resolution

**Cost: ~$0.15 per incident investigation** using Claude Sonnet 4.6 with prompt caching.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Aegis Platform                      │
├──────────────┬──────────────┬──────────────┬─────────┤
│   Frontend   │   API Layer  │  AI Engine   │ Integr. │
│  Next.js 16  │  Go + Fiber  │ Python/Fast  │ Plugins │
│  shadcn/ui   │  REST + WS   │ Claude API   │ Slack   │
│  Tailwind v4 │  Auth/RBAC   │ MCP Server   │ SigNoz  │
├──────────────┴──────────────┴──────────────┴─────────┤
│  PostgreSQL │ ClickHouse │ Redis │ S3 │ Vector DB    │
└─────────────────────────────────────────────────────┘
```

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
cd apps/web && pnpm dev          # Frontend — http://localhost:3000
cd apps/api && go run .          # API      — http://localhost:8080
cd apps/ai-engine && uvicorn main:app --reload  # AI — http://localhost:8000
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui |
| API | Go, Fiber, JWT/OIDC, OpenAPI 3.1 |
| AI Engine | Python, FastAPI, Claude API, MCP, LangGraph |
| Databases | PostgreSQL 16, ClickHouse, Redis 7 |
| Deployment | Docker, Kubernetes (Helm), Terraform |
| CI/CD | GitHub Actions, Conventional Commits |
| Observability | OpenTelemetry |

## Integrations

Aegis connects to your existing stack via a plugin system:

- **Monitoring**: SigNoz, Datadog, Prometheus, Grafana, CloudWatch
- **Incident**: PagerDuty, Opsgenie, Slack, Microsoft Teams
- **Ticketing**: JIRA, Linear, GitHub Issues
- **Cloud**: AWS, GCP, Azure
- **Cost**: OpenCost, Kubecost, AWS Cost Explorer
- **Security**: Trivy, Snyk, Grype
- **CI/CD**: GitHub Actions, CircleCI, ArgoCD

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork the repo, create a branch, make changes, submit a PR
git checkout -b feat/my-feature
# ... make changes ...
git commit -m "feat(module): add my feature"
git push origin feat/my-feature
```

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with care by [June Gu](https://github.com/JIUNG9) | SRE at [acme-corp](https://example.com) (a large tech company)

</div>
