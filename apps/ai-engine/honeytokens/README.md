# Honey Token Beacon — Aegis Layer 0.6

The Honey Token Beacon seeds tripwire secrets into the AI agent's context,
vault, and prompt surface, then scans every outbound byte for them. If a
honey token ever surfaces in an LLM response, an OpenTelemetry span, a
webhook body, or an external log line, Aegis has **hard, unambiguous
evidence** that prompt context leaked.

## Pieces

| File | Purpose |
|------|---------|
| `generator.py` | Builds realistic-looking AWS keys, emails, hostnames, DB passwords, API keys, and PEM blocks. Each token embeds an `AEGIS-HONEY-{sha256[:12]}` marker. |
| `registry.py`  | SQLite registry persisting token metadata across restarts. Thread-safe. |
| `scanner.py`   | `OutboundScanner` (alias: `HoneyTokenDetector`). Aho-Corasick multi-pattern scanner, O(n) in haystack size regardless of registry cardinality. Falls back to a pure-Python automaton when `pyahocorasick` is absent. |
| `seeder.py`    | Idempotently injects tokens into an Obsidian/Markdown vault under a sentinel-guarded footer so real content is never overwritten. |
| `alert.py`     | Fans out hits to an OTel error span, an optional webhook, and a loud stderr banner. |
| `config.py`    | Runtime configuration (`enabled`, `registry_path`, `webhook_url`, `seed_demo_vault`). |

## Threat model

**Catches:** prompt injection leading the LLM to exfiltrate "secrets" it
has seen in context; MCP tools dumping vault pages to unsafe sinks; OTel
exporters accidentally forwarding prompt text; log aggregation pipelines
echoing tool I/O.

**Does NOT catch:** secrets the agent never saw (honey tokens must be
seeded into context first); leaks through side channels the scanner is
not wired into; steganographic exfiltration that mutates the marker.

Because the marker `AEGIS-HONEY-` is unique to this system, scanner hits
have near-zero false-positive rate — treat every hit as a confirmed
incident.
