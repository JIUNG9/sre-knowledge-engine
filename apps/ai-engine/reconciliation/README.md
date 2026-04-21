# Reconciliation engine — Layer 5

Cross-source document reconciliation for Aegis. Surfaces four read-only
MCP tools that help Claude find, compare, and flag documentation drift
across the systems most SRE teams accumulate over time: local Obsidian
vaults, Confluence spaces, GitHub wikis, and Slack-pinned messages.

## Architecture

```
 ┌──────────────┐ ┌─────────────┐ ┌──────────────┐ ┌─────────────┐
 │ Obsidian     │ │ Confluence  │ │ GitHub Wiki  │ │ Slack Pins  │
 │ (vault .md)  │ │ (REST v2)   │ │ (local clone)│ │ (stub)      │
 └──────┬───────┘ └──────┬──────┘ └──────┬───────┘ └──────┬──────┘
        └───────── DocSource base ────────────────────────┘
                             │
                       Reconciler
                    ┌────────┴────────┐
            string diff         LLMRouter (Layer 0.4)
                                    │
                              Ollama / Claude
```

Every source is a subclass of `DocSource` — adding Notion, Google Drive,
or Jira comments is a 30-line exercise.

## Tools (all scope="read")

| Tool | Purpose |
|------|---------|
| `find_docs` | Freshness-ranked search across every source. |
| `reconcile_docs` | Full cross-source comparison with flagged contradictions. |
| `detect_stale_docs` | Per-source staleness sweep. Explains *why* a doc is stale. |
| `check_doc_links` | Validates internal + external links. Honours robots.txt. |

## Safety

* All tools register via `@scoped_tool("read")` — they can never
  mutate a source and never appear in the `write` or `blocked` scope
  load.
* LLM calls flow through the Layer 0.4 `LLMRouter` with
  `sensitivity_override=True`, routing doc bodies to Ollama by
  default so your company's runbook content never leaves the box.
* Link-check HEAD probes honour `robots.txt` and use a 3-second
  timeout to avoid becoming a DoS tool.

## Tests

`pytest reconciliation/tests` covers the drift scorer, all four
sources, and the reconciler with both happy-path and
LLM-unavailable paths. No test touches the network — external HTTP
is mocked via `respx`.
