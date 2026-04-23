| # | Layer | Status | What it does |
|---|-------|--------|--------------|
| 1 | **LLM Wiki Engine** | Built, shipped | Karpathy-pattern knowledge base. Reads Confluence, GitHub, SigNoz, Slack. Synthesizes one canonical markdown page per entity. Renders to `aegis-wiki` repo. Never goes stale because it never stops updating. |
| 2 | **SigNoz Connector** | Planned | Pulls ClickHouse-backed traces, metrics, and logs from SigNoz. Normalizes incident timelines. Feeds Layer 1 with observability data. |
| 3 | **Claude Control Tower** | Planned | MCP-based agent control plane. Tiered risk model (read-safe / write-requires-approval / blocked). Slack-in-the-loop approval flow. Full audit trail. |
| 4 | **Production Guardrails** | Planned | Pre-flight checks on Terraform plans, Kubernetes manifests, AWS IAM policies. Triangulates between Claude, a local Ollama model, and Codex as an adversarial reviewer. Blocks destructive changes without explicit approval. |
| 5 | **MCP Document Reconciliation** | Planned | Detects contradictions between Confluence, GitHub runbooks, and Slack incident post-mortems. Opens PRs to fix. Keeps the knowledge graph from drifting. |
