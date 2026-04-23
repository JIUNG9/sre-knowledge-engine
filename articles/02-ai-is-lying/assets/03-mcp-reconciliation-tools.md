| Tool | Input | Output | Cadence |
|---|---|---|---|
| `confluence_sync` | Space key, API token | Ingested pages with source-typed metadata | Daily |
| `github_docs_scan` | Repo list, glob patterns | Runbooks, ARCHITECTURE.md, ADRs | On-push webhook |
| `incident_history_sync` | SigNoz/PagerDuty API keys | Postmortem-grade incident pages | Hourly |
| `docs_lint` | Vault path | Contradictions + staleness + coverage gaps | On-demand |
