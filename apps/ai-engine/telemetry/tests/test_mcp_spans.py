"""Tests for telemetry.mcp_spans — read/write/blocked scope semantics."""

from __future__ import annotations

import pytest
from opentelemetry.trace import StatusCode

from telemetry import trace_mcp_tool
from telemetry.mcp_spans import (
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTCOME,
    ATTR_TOOL_SCOPE,
    ATTR_TOOL_TARGET,
)


def test_read_scope_is_success(memory_exporter) -> None:
    """scope=read produces a successful span with outcome=success."""
    with trace_mcp_tool(
        "kubectl_get_pods",
        scope="read",
        target_resource="k8s://pods/default",
    ) as tool:
        pass

    spans = memory_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    attrs = dict(span.attributes or {})
    assert attrs[ATTR_TOOL_NAME] == "kubectl_get_pods"
    assert attrs[ATTR_TOOL_SCOPE] == "read"
    assert attrs[ATTR_TOOL_TARGET] == "k8s://pods/default"
    assert attrs[ATTR_TOOL_OUTCOME] == "success"
    assert span.status.status_code == StatusCode.OK


def test_blocked_scope_marks_span_error(memory_exporter) -> None:
    """scope=blocked ALWAYS marks the span as ERROR for security dashboards."""
    with trace_mcp_tool(
        "aws_iam_create_user",
        scope="blocked",
        target_resource="aws://iam/users",
    ) as tool:
        pass

    span = memory_exporter.get_finished_spans()[0]
    attrs = dict(span.attributes or {})
    assert attrs[ATTR_TOOL_SCOPE] == "blocked"
    assert attrs[ATTR_TOOL_OUTCOME] == "denied"
    assert span.status.status_code == StatusCode.ERROR


def test_write_scope_success(memory_exporter) -> None:
    """scope=write can succeed — approval is tracked by outcome, not status."""
    with trace_mcp_tool(
        "slack_post_message",
        scope="write",
        target_resource="slack://channels/incidents",
    ) as tool:
        tool.set_approval_required(True)
        tool.set_outcome("success")

    span = memory_exporter.get_finished_spans()[0]
    attrs = dict(span.attributes or {})
    assert attrs[ATTR_TOOL_SCOPE] == "write"
    assert attrs[ATTR_TOOL_OUTCOME] == "success"
    assert attrs["aegis.mcp.tool.approval_required"] is True
    assert span.status.status_code == StatusCode.OK


def test_exception_in_tool_marks_error(memory_exporter) -> None:
    class ToolBoom(Exception):
        pass

    with pytest.raises(ToolBoom):
        with trace_mcp_tool("prom_query", scope="read") as tool:
            tool.set_target("prom://query")
            raise ToolBoom("upstream 500")

    span = memory_exporter.get_finished_spans()[0]
    attrs = dict(span.attributes or {})
    assert attrs[ATTR_TOOL_OUTCOME] == "exception"
    assert span.status.status_code == StatusCode.ERROR
    assert any(ev.name == "exception" for ev in span.events)


def test_invalid_scope_raises(memory_exporter) -> None:
    with pytest.raises(ValueError):
        with trace_mcp_tool("x", scope="oops"):  # type: ignore[arg-type]
            pass


def test_custom_outcome_is_preserved(memory_exporter) -> None:
    """Caller-set outcome is not overwritten by the default 'success'."""
    with trace_mcp_tool("prom_query", scope="read") as tool:
        tool.set_outcome("timeout")

    span = memory_exporter.get_finished_spans()[0]
    attrs = dict(span.attributes or {})
    assert attrs[ATTR_TOOL_OUTCOME] == "timeout"
