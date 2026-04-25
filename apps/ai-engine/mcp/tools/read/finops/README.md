# Aegis FinOps MCP Tools (Phase 2.2)

Read-only MCP tools that let Claude answer cloud-cost questions by
querying three production FinOps backends: AWS Cost Explorer,
OpenCost, and Kubecost.

## Tool catalog

| Tool | Backend | Purpose |
| --- | --- | --- |
| `query_aws_costs` | AWS Cost Explorer (`boto3 ce`) | Unblended costs in a date window, with optional service filter and GroupBy dimensions. |
| `query_opencost_allocation` | OpenCost HTTP API | Kubernetes allocation by namespace / controller / pod / node / cluster. |
| `query_kubecost_allocation` | Kubecost HTTP API | Kubernetes allocation, supports Kubecost-specific aggregates like `label:team`. |
| `top_spenders` | Composite | Fan-out to every configured backend, returns a ranked top-N list. |
| `find_cost_anomalies` | Composite | Pulls a daily series and flags z-score spikes. |

Every tool is registered with `@scoped_tool("read")` — they appear
in the MCP read manifest and never in the write/blocked manifest.
Each tool returns a plain JSON-serialisable `dict`, never a
Pydantic model, so the MCP serving layer can stream the result back
to Claude without extra marshalling.

## Backends supported

1. **AWS Cost Explorer** (most common) — needs `boto3` and standard
   AWS credentials. Install with the optional extra:
   `pip install aegis-ai-engine[finops]`.
2. **OpenCost** — point `AEGIS_FINOPS_OPENCOST_URL` at your cluster's
   OpenCost service (default port 9003).
3. **Kubecost** — point `AEGIS_FINOPS_KUBECOST_URL` at the
   cost-analyzer service (default port 9090).

When a backend is not configured (missing URL, missing credentials,
HTTP error), the tool returns `{"status": "unavailable", ...}` with
a human-readable reason. The agent can reason over this and fall
back to another provider without crashing the investigation loop.

## Sample Claude prompt

> "What's the top spend across our cloud and Kubernetes clusters
> this week, and was there an anomaly?"

Expected tool-use sequence:

```
top_spenders(provider="all", limit=10, window="7d")
  -> returns ranked spenders across aws / opencost / kubecost
find_cost_anomalies(provider="aws", lookback_days=30, sensitivity=2.0)
  -> returns z-score spikes with dates and amounts
```

All examples and tests use generic placeholders (`acme-corp`,
`customer-xyz`) — no employer-specific names in this package.
