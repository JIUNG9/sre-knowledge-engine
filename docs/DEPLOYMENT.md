# Aegis Deployment Guide

**Version**: 4.0
**Audience**: anyone cloning `github.com/JIUNG9/aegis` and wanting to run it somewhere real.

Aegis ships three deployment tiers. They differ in how real the data is, how strict the compliance posture needs to be, and how much infrastructure the operator has to provide. Pick the tier that matches your situation. Don't pick the tier "above" your situation — Layer 0 assumes the tier matches reality, and an over-configured deployment burns money without adding safety.

| Tier | Use case | Real data? | LLM backend | Audit requirements |
| --- | --- | --- | --- | --- |
| **A — Local / Homelab** | Learning, demo, contributor dev | No (LocalStack + seeders) | Claude API or Ollama, either works | None |
| **B — Personal Cloud** | Consultant, hobbyist, bootstrapped startup | Yes, but only *your* data | Claude API by default; Ollama optional | Light — keep audit logs; no external reporting |
| **C — Enterprise Sandbox** | Team deployment, regulated org (PIPA / GDPR / HIPAA / SOC2) | Yes, company prod telemetry | Local Ollama for sensitive data; Claude API for sanitized only | Full — exportable OTel audit trail, honey tokens, kill switch, approval gates |

The rest of this document walks through each tier in turn.

---

## Tier A — Local / Homelab

You want to see Aegis work. You do not want to wire up any real credentials.

### Prerequisites

- Docker + Docker Compose (or Podman with a compat shim)
- ~8 GB free RAM
- No cloud account required
- No Anthropic API key required (the demo uses Ollama when you skip `ANTHROPIC_API_KEY`)

### Boot

```bash
git clone https://github.com/JIUNG9/aegis
cd aegis
make demo
```

This boots:

- LocalStack — mock AWS (S3, EC2, IAM, CloudWatch Logs)
- SigNoz all-in-one (ClickHouse + query-service + frontend + otel-collector)
- OpenTelemetry Demo (astronomy-shop) generating traces/logs/metrics
- A FastAPI "confluence-mock" serving 20 fake runbook pages with deliberate staleness
- Redis (for the Layer 0.3 kill switch)
- `aegis-api` (Python + FastAPI)
- `aegis-web` (Next.js 16)

Optionally add Ollama with a profile:

```bash
make demo PROFILE=ollama
```

### What you see

- `http://localhost:3000` — Aegis dashboard (incidents, FinOps, on-call, etc.)
- `http://localhost:3301` — SigNoz UI, populated by astronomy-shop telemetry
- `http://localhost:8080` — OpenTelemetry Demo frontend

Synthetic incidents are skewed to Monday 9 AM so Article #6's pattern analyzer has something to find. Confluence fixtures contain contradictions so Layer 5's reconciliation tools have something to report.

### Teardown

```bash
make demo-down       # stop services, keep volumes
make demo-reset      # stop services, wipe volumes
```

---

## Tier B — Personal Cloud

You want to run Aegis against real data in your own environment. Consultant, freelance SRE, or bootstrapped startup scenario.

### Prerequisites

- A personal AWS account you pay for yourself (not your employer's account)
- `ANTHROPIC_API_KEY` for a personal Anthropic billing account
- Your own SigNoz instance (self-hosted or SigNoz Cloud)
- Optionally Confluence with read-only API token

### Configuration

Copy the example config and fill in the pieces:

```bash
cp aegis.config.example.yaml aegis.config.yaml
```

Minimum working Tier B config:

```yaml
# aegis.config.yaml — Tier B
deployment:
  tier: B
  environment: production  # your prod, not your company's

llm_router:
  sensitive_backend: claude        # or ollama if you run one locally
  sanitized_backend: claude
  claude_model: claude-opus-4-7
  auto_detect_sensitive: true

pii_proxy:
  enabled: true
  provider: hybrid
  custom_patterns: []

killswitch:
  backend: redis
  redis_url: redis://localhost:6379
  revoke_aws_on_panic: false   # don't auto-revoke in Tier B; your call

mcp:
  load_read: true
  load_write: false            # no write tools until you opt in per-tool

telemetry:
  enabled: true
  exporter: otlp
  otlp_endpoint: http://localhost:4318   # your local OTel collector

connectors:
  signoz:
    base_url: https://signoz.your-org.com
    api_key: ${AEGIS_SIGNOZ_API_KEY}
```

### IAM

Apply the Tier B IAM template:

```bash
# Preview the IAM policy, do NOT apply it automatically:
cat deploy/iam/aws/readonly-policy.json

# When you are satisfied, create the role manually or via your own Terraform:
aws iam create-role --role-name aegis-readonly --assume-role-policy-document file://deploy/iam/aws/trust-policy.json
aws iam put-role-policy --role-name aegis-readonly --policy-name aegis-read --policy-document file://deploy/iam/aws/readonly-policy.json
```

Validate with the shipped validator first:

```bash
python deploy/iam/validator.py deploy/iam/aws/readonly-policy.json
```

It will fail loudly if the policy has any Allow statement for a mutating verb, missing Deny guards on secretsmanager/iam/kms/organizations, or wildcard Allow on wildcard Resource. Don't apply a policy that doesn't pass.

### Run

```bash
docker compose up -d redis
pnpm install
ANTHROPIC_API_KEY=... AEGIS_SIGNOZ_API_KEY=... pnpm dev
```

---

## Tier C — Enterprise Sandbox (Regulated Deployment)

Your company has real compliance requirements. PIPA, GDPR, HIPAA, APPI, DPDP — pick your acronym. This section is about the deployment shape that keeps Aegis on the right side of them.

### The hard architectural rule

**Real production personal data never crosses a jurisdictional boundary.** Period. If your data resides in Korea, it stays in Korea. If your users are EU, your processing stays EU. The way Aegis enforces this is by routing all *sensitive* prompts to a locally-hosted Ollama instance and only sending *sanitized* prompts to the Claude API.

This is Layer 0.4 (LLM Router) doing its job.

### Reference architecture

```
┌─ Your VPC, your jurisdiction ───────────────────────────────────┐
│                                                                  │
│   SigNoz ──┐                                                     │
│   Conflnc ─┼──▶ Aegis agent ◀──▶ Ollama (llama3.1:70b)           │
│   AWS APIs─┘        │                                            │
│                     │ only sanitized                              │
│                     ▼                                             │
│                 PII Proxy ──▶ (outbound HTTPS)                   │
│                                     │                             │
└─────────────────────────────────────┼─────────────────────────────┘
                                      ▼
                              api.anthropic.com
                              (only sees <USER_1>, <HOST_1>, etc.)
```

### Configuration

Minimum Tier C config:

```yaml
# aegis.config.yaml — Tier C
deployment:
  tier: C
  environment: production
  jurisdiction: KR                 # or EU, JP, US-CA, etc.

llm_router:
  sensitive_backend: ollama
  sanitized_backend: claude
  ollama_url: http://ollama.internal:11434   # inside your VPC
  ollama_model: llama3.1:70b
  claude_model: claude-opus-4-7
  auto_detect_sensitive: true
  always_local: false                          # flip to true for maximum conservatism
  fallback_to_cloud_on_local_failure: false    # NEVER TRUE IN TIER C
  sensitive_keywords:
    - your-company-internal-domain
    - customer-identifier-prefix

pii_proxy:
  enabled: true
  provider: hybrid                # regex + Presidio
  custom_patterns:
    - '\bprod-[a-z0-9-]+\.yourcorp\.internal\b'
    - '\byourcorp_[a-z]+_prod\b'

killswitch:
  backend: redis
  redis_url: redis://redis.internal:6379
  revoke_aws_on_panic: true       # Tier C: opt in
  aws_role_arn: arn:aws:iam::123456789012:role/aegis-readonly

honeytokens:
  enabled: true
  registry_path: /var/lib/aegis/honeytokens.db
  webhook_url: https://your-alert-endpoint
  seed_demo_vault: false          # production vault — don't seed demo tokens

mcp:
  load_read: true
  load_write: false
  blocked_tools:
    - terraform_apply
    - kubectl_delete
    - kubectl_apply_destructive
    - aws_iam_delete
    - helm_install

telemetry:
  enabled: true
  exporter: otlp
  otlp_endpoint: http://otel-collector.internal:4318
  sample_ratio: 1.0               # full sampling — audit trail must be complete

guardrails:
  policy_file: /etc/aegis/guardrails.policy.yaml
  audit_log_path: /var/log/aegis/audit.jsonl
  default_max_tier: SUGGEST       # Tier C default: suggest only, no auto-execute

connectors:
  signoz:
    base_url: https://signoz.yourcorp.internal
    api_key: ${AEGIS_SIGNOZ_API_KEY}
    verify_tls: true
```

### IAM

Use the Tier C IAM templates with session-policy intersection. Never grant the agent role access to production write APIs — not even for "emergency" use.

```bash
python deploy/iam/validator.py \
    deploy/iam/aws/readonly-policy.json \
    deploy/iam/aws/trust-policy.json \
    deploy/iam/aws/session-policy-example.json
```

All three must pass validation before you apply.

### Audit posture

Every LLM call, every MCP tool invocation, every kill-switch trip goes into the audit trail. For Tier C your SIEM must ingest:

- OTel spans with `service.name=aegis` (backed by OTLP collector)
- Append-only JSONL at `guardrails.audit_log_path`
- Append-only JSONL at `killswitch.audit_log_path` (from Layer 0.3)

To prove to a regulator that sensitive data did not cross a border, query:

```traceql
{ resource.service.name = "aegis"
  && span.gen_ai.system = "anthropic" }
| count_over_time(1d)
```

If that count is zero for the period in question, you have evidence. If it is non-zero, the spans include the redacted request size so you can show the payloads were sanitized first.

### Compliance appendix

| Framework | Territorial scope | Key Tier-C control |
| --- | --- | --- |
| **Korean PIPA (amended April 2026)** | Korean residents' personal info | Local Ollama for sensitive data; OTel trace of `gen_ai.system=anthropic` count; explicit consent architecture for any sanitized path |
| **GDPR** | EU data subjects, regardless of operator residence | Same as PIPA plus Schrems-II supplementary measures argument for sanitized transfers |
| **APPI (Japan, 2022)** | Japanese data subjects | Local Ollama + consent notice |
| **DPDP (India, 2023)** | Sensitive categories require localization | Local Ollama mandatory for sensitive categories |
| **HIPAA** | US PHI | Local Ollama sidesteps BAA requirement entirely for the hot path |
| **SOC 2** | Audit framework | Full Tier C audit posture satisfies CC6.1, CC7.1, CC7.2, CC8.1 |

This is an engineering guide, not legal advice. Your lawyer still has work to do — but they will have a defensible technical architecture to work from.

---

## Cost envelope per tier

| Tier | Monthly cost | Notes |
| --- | --- | --- |
| A (local) | ~$0 | Your laptop + Docker |
| B (personal cloud) | ~$15–$50 | Small EC2 + Claude API + SigNoz Cloud free tier |
| C (enterprise) | ~$500–$2000+ | g5.12xlarge for Ollama ($5/hr on-demand, $1.50/hr spot) dominates; self-hosted SigNoz is free |

The Ollama cost in Tier C is what makes the compliance posture possible. It pays for itself versus a Claude-API-only deployment at around 100 investigations/day — so for any non-trivial deployment, the compliance-grade architecture is actually cheaper than the naive one.

---

## Upgrading between tiers

You can start at Tier A for learning, move to Tier B when you want to analyze your own infrastructure, and move to Tier C when the deployment goes inside a company. The config is additive — each tier enables additional Layer 0 features, not replaces them.

No tier downgrade is supported. Once you have real data flowing through Aegis, you should not demote the configuration — it leaves audit evidence of a period when sensitive data was not properly handled.

---

## Getting help

- Open an issue on [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis) with the tier you are attempting and the error.
- Read the Layer 0 articles (#9 PII proxy, #10 honey tokens, #11 PIPA case study) before filing — most deployment questions are answered there.
- Run `aegis status` — it will print the active Layer 0 configuration and flag inconsistencies (e.g. Tier C with `fallback_to_cloud_on_local_failure: true` is flagged).

---

*This document is authoritative as of Aegis v4.0. Breaking config changes will be listed in `CHANGELOG.md` under each minor version.*
