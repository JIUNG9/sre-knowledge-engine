# Aegis Demo Mode (Layer 0.8)

Self-contained local demo of the entire Aegis stack.
Clone the repo, run one command, and explore an AI SRE platform
fed by synthetic incidents — no real credentials, no cloud account,
no Confluence or SigNoz subscriptions required.

## Prerequisites

- Docker 24+ and Docker Compose v2
- 8 GB free RAM (stack is capped around that)
- ~6 GB free disk for images and volumes
- Python 3.10+ on the host (for seed scripts; optional — the
  `make demo-seed` target will skip gracefully if missing)
- Ports free: `3000, 3301, 4317, 4318, 4566, 6379, 8000, 8080, 8090`

## Quick start

```bash
cd deploy/demo
make demo
```

This boots the full stack, seeds 24h of synthetic incidents, 20
runbook pages, fake AWS resources, and honeytokens, then prints
URLs for every UI.

## What runs

| Service             | Port(s)             | Purpose                                  |
| ------------------- | ------------------- | ---------------------------------------- |
| aegis-web           | `3000`              | Aegis dashboard (Next.js)                |
| aegis-api           | `8000`              | AI engine + REST API (FastAPI)           |
| signoz-frontend     | `3301`              | SigNoz observability UI                  |
| signoz-otel-collector | `4317, 4318`      | OTLP ingest                              |
| otel-demo           | `8080`              | Astronomy-shop synthetic traffic         |
| localstack          | `4566`              | Fake S3 / EC2 / IAM / CloudWatch Logs    |
| confluence-mock     | `8090`              | 20 canned runbook pages                  |
| redis               | `6379`              | Kill switch + cache                      |
| ollama (optional)   | `11434`             | Local LLM (`make demo-ollama`)           |

## Explore

- **Aegis dashboard** — open http://localhost:3000, click _Incidents_
  for the synthetic list, _FinOps_ for LocalStack cost data, _On-Call_
  for the fake runbook wiki.
- **SigNoz** — http://localhost:3301 shows live OTel traces/logs/metrics
  flowing from the astronomy shop demo.
- **Patterns demo** — incidents are skewed toward Mondays 9am UTC so
  the "recurring pattern" article has reproducible data.

## Make targets

| Target            | Description                                  |
| ----------------- | -------------------------------------------- |
| `make demo`       | Boot + seed + print URLs                     |
| `make demo-up`    | Boot only                                    |
| `make demo-seed`  | (re)run all seed scripts                     |
| `make demo-down`  | Stop stack, preserve volumes                 |
| `make demo-reset` | Stop + wipe all demo volumes                 |
| `make demo-logs`  | Tail all service logs                        |
| `make demo-test`  | Run smoke tests                              |
| `make demo-ollama`| Boot with local LLM profile (adds ~2GB RAM)  |

## Troubleshooting

- **Port already in use** — stop the conflicting service or remap in
  `docker-compose.demo.yml`.
- **Clickhouse OOM** — bump Docker Desktop memory allocation to 10GB.
- **Slow boot on first run** — images total ~3GB; subsequent boots
  reuse the layer cache and complete in ~90s.
- **Seeding failed** — run `make demo-seed` after the stack is fully
  healthy (check `docker compose -f docker-compose.demo.yml ps`).

## Safety

The entire stack is air-gapped: no real cloud calls, no outbound
telemetry except when you opt into Ollama image pulls. Tearing down
with `make demo-reset` wipes every named volume.
