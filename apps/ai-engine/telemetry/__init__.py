"""Aegis OpenTelemetry GenAI tracing — Layer 0.5.

Public API:
    setup_telemetry   — install global TracerProvider (idempotent)
    trace_llm_call    — context manager for one LLM call (GenAI semconv)
    trace_mcp_tool    — context manager for one MCP tool invocation
    TelemetryConfig   — declarative configuration

Example:
    from telemetry import setup_telemetry, trace_llm_call, trace_mcp_tool

    setup_telemetry()  # console exporter by default

    with trace_llm_call("claude-opus-4-7", "chat") as llm:
        llm.set_request(max_tokens=4096, temperature=0.2)
        resp = client.messages.create(...)
        llm.set_response(
            model=resp.model,
            response_id=resp.id,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    with trace_mcp_tool("kubectl_get_pods", scope="read") as tool:
        tool.set_target("k8s://pods/prod")
        tool.set_outcome("success")

Design goals:
    * Zero overhead when TelemetryConfig.enabled=False.
    * Idempotent setup — safe to call from FastAPI lifespan, CLI, tests.
    * Default console exporter so new developers see traces with no infra.
    * OTLP exporter honors OTEL_EXPORTER_OTLP_ENDPOINT / _HEADERS env vars.
"""

from telemetry.config import TelemetryConfig
from telemetry.llm_spans import LLMSpanHandle, trace_llm_call
from telemetry.mcp_spans import MCPSpanHandle, Scope, trace_mcp_tool
from telemetry.setup import (
    get_active_config,
    is_initialized,
    reset_for_tests,
    setup_telemetry,
)

__all__ = [
    "LLMSpanHandle",
    "MCPSpanHandle",
    "Scope",
    "TelemetryConfig",
    "get_active_config",
    "is_initialized",
    "reset_for_tests",
    "setup_telemetry",
    "trace_llm_call",
    "trace_mcp_tool",
]
