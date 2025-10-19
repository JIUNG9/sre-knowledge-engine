# ADR-003: Hybrid Event-Driven + Batch Architecture for AI Agent

## Status

Accepted

## Context

Aegis uses Claude API for AI-powered incident investigation and health analysis. We need to decide how the AI agent interacts with the monitoring stack:

1. **Polling**: Agent queries SigNoz/metrics every N minutes, regardless of incidents
2. **Event-driven**: Agent only activates when a webhook alert arrives
3. **Hybrid**: Real-time investigation on alerts + periodic batch analysis

Token costs are a primary concern. Claude Sonnet 4.6 costs $3/$15 per million input/output tokens. Unnecessary API calls waste budget.

## Decision

We chose the **Hybrid Event-Driven + Scheduled Batch** architecture.

### Real-time path (webhooks)
- SigNoz, Datadog, Prometheus send webhook alerts to Aegis
- Alert processor deduplicates and correlates
- Only HIGH/CRITICAL severity triggers Claude API investigation
- Cost: ~$0.15 per incident investigation

### Batch path (scheduled)
- Cron job every 6 hours collects metrics summaries
- Uses Claude Batch API (50% discount) + prompt caching (90% discount on cached content)
- Generates health reports, trend analysis, cost anomalies
- Cost: ~$2-5/day

### Cost projection
- ~$10-15/month total for 20 incidents + 4x daily batch analysis
- Compared to polling every 5min: $150-500/month (wasteful when no incidents)

## Consequences

### Positive

- 10-50x cheaper than pure polling
- Real-time response for critical incidents (<10s latency)
- Batch analysis catches slow-burn issues that individual alerts miss
- Prompt caching + batch API combine for up to 95% cost reduction

### Negative

- Two code paths to maintain (webhook handler + batch worker)
- 6-hour delay for non-alert insights (configurable)
- Requires webhook configuration in each monitoring tool

### Neutral

- SigNoz natively supports Prometheus Alertmanager webhooks, so integration is straightforward
