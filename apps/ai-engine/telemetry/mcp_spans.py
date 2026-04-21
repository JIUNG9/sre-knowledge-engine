"""OpenTelemetry spans for Aegis MCP tool invocations.

Each MCP tool call gets its own span. Scope is the critical attribute: it
proves to auditors that ``blocked`` tools were refused and ``write`` tools
were gated by approval. A scope=``blocked`` span is always marked ERROR so
it shows up in "failed span" dashboards.

The ``aegis.mcp.*`` namespace is a vendor extension on top of OTel GenAI
semconv. We stay out of the ``gen_ai.*`` namespace because MCP tools are
not themselves LLM calls — they're side-effectful actions the LLM requested.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Literal

if TYPE_CHECKING:
    from opentelemetry.trace import Span

logger = logging.getLogger("aegis.telemetry.mcp")

Scope = Literal["read", "write", "blocked"]

# Aegis-specific attribute keys (vendor namespace).
ATTR_TOOL_NAME = "aegis.mcp.tool.name"
ATTR_TOOL_SCOPE = "aegis.mcp.tool.scope"
ATTR_TOOL_TARGET = "aegis.mcp.tool.target_resource"
ATTR_TOOL_OUTCOME = "aegis.mcp.tool.outcome"
ATTR_TOOL_DURATION_MS = "aegis.mcp.tool.duration_ms"
ATTR_TOOL_APPROVAL_REQUIRED = "aegis.mcp.tool.approval_required"


class MCPSpanHandle:
    """Handle returned by ``trace_mcp_tool`` for recording outcome + metadata."""

    def __init__(self, otel_span: "Span | None", scope: Scope) -> None:
        self._span = otel_span
        self._scope = scope
        self._outcome: str | None = None

    @property
    def span(self) -> "Span | None":
        return self._span

    @property
    def scope(self) -> Scope:
        return self._scope

    def _set(self, key: str, value: Any) -> None:
        if self._span is None or not self._span.is_recording():
            return
        if value is None:
            return
        self._span.set_attribute(key, value)

    def set_target(self, target_resource: str) -> None:
        """Record what resource the tool touched (e.g. ``k8s://pods/default``)."""
        self._set(ATTR_TOOL_TARGET, target_resource)

    def set_outcome(self, outcome: str) -> None:
        """Record the semantic outcome: ``success``, ``denied``, ``timeout``, etc."""
        self._outcome = outcome
        self._set(ATTR_TOOL_OUTCOME, outcome)

    def set_approval_required(self, required: bool) -> None:
        self._set(ATTR_TOOL_APPROVAL_REQUIRED, required)

    def set_attribute(self, key: str, value: Any) -> None:
        self._set(key, value)


@contextmanager
def trace_mcp_tool(
    tool_name: str,
    scope: Scope,
    *,
    target_resource: str | None = None,
) -> Iterator[MCPSpanHandle]:
    """Create an OTel span for one MCP tool invocation.

    Args:
        tool_name: Name of the MCP tool being invoked.
        scope: ``"read"`` | ``"write"`` | ``"blocked"``. Scope=``"blocked"``
            means the tool was refused — span is marked ERROR automatically
            so security dashboards can alert on it.
        target_resource: Optional URI-style identifier for what the tool
            touched (e.g. ``"aws://s3/bucket/foo"``, ``"k8s://deployment/bar"``).

    Yields:
        ``MCPSpanHandle`` — call ``set_outcome(...)`` and ``set_target(...)``
        as execution progresses.

    Always records exceptions. Scope=``"blocked"`` always ends with ERROR
    status regardless of exception, proving the refusal in the trace.
    """
    if scope not in ("read", "write", "blocked"):
        raise ValueError(
            f"scope must be 'read', 'write', or 'blocked', got {scope!r}"
        )

    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind, Status, StatusCode
    except ImportError:  # pragma: no cover
        yield MCPSpanHandle(None, scope)
        return

    tracer = trace.get_tracer("aegis.telemetry.mcp", "0.4.0")
    span_name = f"mcp.tool {tool_name}"

    with tracer.start_as_current_span(span_name, kind=SpanKind.INTERNAL) as span:
        handle = MCPSpanHandle(span, scope)
        handle.set_attribute(ATTR_TOOL_NAME, tool_name)
        handle.set_attribute(ATTR_TOOL_SCOPE, scope)
        if target_resource is not None:
            handle.set_target(target_resource)

        try:
            yield handle
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            if handle._outcome is None:
                handle.set_outcome("exception")
            raise
        else:
            if scope == "blocked":
                # Blocked tools are refusals — always ERROR in the trace.
                if handle._outcome is None:
                    handle.set_outcome("denied")
                span.set_status(
                    Status(StatusCode.ERROR, "mcp tool blocked by policy")
                )
            else:
                if handle._outcome is None:
                    handle.set_outcome("success")
                span.set_status(Status(StatusCode.OK))
