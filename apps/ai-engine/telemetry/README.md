# Aegis Telemetry — OpenTelemetry GenAI Tracing (Layer 0.5)

Emits OTel spans that conform to the [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
for every LLM call, and vendor-extension `aegis.mcp.*` spans for every MCP
tool invocation. The goal is that any deployer can export these traces to
Datadog, Honeycomb, Jaeger, Grafana Tempo, or SigNoz and *prove* to their
security team: **"this agent only read; it never wrote."**

## Quick start

```python
from telemetry import setup_telemetry, trace_llm_call, trace_mcp_tool

setup_telemetry()  # console exporter by default; idempotent

with trace_llm_call("claude-opus-4-7", "chat", max_tokens=4096) as llm:
    resp = client.messages.create(...)
    llm.set_response(
        model=resp.model, response_id=resp.id,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
    )

with trace_mcp_tool("kubectl_get_pods", scope="read") as tool:
    tool.set_target("k8s://pods/prod")
```

Set `OTEL_EXPORTER_OTLP_ENDPOINT=https://api.honeycomb.io` (plus
`OTEL_EXPORTER_OTLP_HEADERS=x-honeycomb-team=...`) to ship to any OTLP
backend. `setup_telemetry()` is idempotent; `enabled=False` makes every
span a no-op with zero overhead.

## Prove no write tools were called in the last 24h

Datadog / Honeycomb / Tempo LogQL / SigNoz all support a query like:

```
service.name:"aegis" span.name:"mcp.tool *" @aegis.mcp.tool.scope:("write" OR "blocked")
```

Grafana Tempo TraceQL:

```
{ resource.service.name = "aegis"
  && name =~ "mcp.tool.*"
  && span.aegis.mcp.tool.scope =~ "write|blocked" }
```

If the result count is zero across the last 24h, the agent was strictly
read-only. Blocked spans are always `status=ERROR`, so a "failed span"
dashboard doubles as a refusal audit log.

## Attributes we emit

| Scope | Attribute |
|---|---|
| GenAI (stable) | `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.request.max_tokens`, `gen_ai.request.temperature`, `gen_ai.response.model`, `gen_ai.response.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| GenAI (optional) | `gen_ai.request.top_p`, `gen_ai.response.finish_reasons` |
| Aegis MCP | `aegis.mcp.tool.name`, `aegis.mcp.tool.scope` (read / write / blocked), `aegis.mcp.tool.target_resource`, `aegis.mcp.tool.outcome`, `aegis.mcp.tool.approval_required` |

### Attributes we intentionally do NOT emit

- `gen_ai.prompt` / `gen_ai.completion` (raw prompts & completions) — PII
  and secrets risk. Emitting them by default would leak customer data into
  trace backends. Plan to expose these behind an opt-in flag in Layer 2.
- `gen_ai.request.stop_sequences` — low signal, high cardinality.
- `gen_ai.conversation.id` — not supplied by the Anthropic SDK uniformly;
  will be added when we standardize on the Aegis investigation id.
