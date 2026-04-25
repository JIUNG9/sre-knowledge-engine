"""Unit tests for the MCP ToolManifest and @scoped_tool decorator."""

from __future__ import annotations

import pytest

from mcp.manifest import ToolManifest
from mcp.scope_config import DEFAULT_BLOCKED_TOOL_NAMES, MCPScopeConfig


# Import the tool packages so their decorators run against the shared
# manifest. The assertions below use the package-level manifest.
import mcp.tools.blocked  # noqa: F401
import mcp.tools.read  # noqa: F401
import mcp.tools.write  # noqa: F401
from mcp.manifest import manifest as shared_manifest
from mcp.scoped_tool import scoped_tool


# ---------------------------------------------------------------------- #
# Defaults
# ---------------------------------------------------------------------- #


def test_default_config_loads_read_only():
    """Default config surfaces READ tools and NOT write or blocked."""
    config = MCPScopeConfig()
    read_tools = shared_manifest.load_scope("read", config)
    write_tools = shared_manifest.load_scope("write", config)

    read_names = {t.name for t in read_tools}
    assert "log_search" in read_names
    assert "metric_query" in read_names
    assert "runbook_lookup" in read_names

    # Write tools require opt-in; default config does not enable them.
    assert write_tools == []


def test_load_write_enables_write_tools():
    """Setting ``load_write=True`` surfaces write-scope tools."""
    config = MCPScopeConfig(load_write=True)
    write_tools = shared_manifest.load_scope("write", config)

    write_names = {t.name for t in write_tools}
    assert "slack_post" in write_names
    assert "jira_create_ticket" in write_names


# ---------------------------------------------------------------------- #
# Absolute blocking
# ---------------------------------------------------------------------- #


def test_blocked_tools_never_appear_even_with_load_write_true():
    """Even with load_write=True, blocked names are absent from every scope."""
    config = MCPScopeConfig(load_write=True)
    read_tools = shared_manifest.load_scope("read", config)
    write_tools = shared_manifest.load_scope("write", config)
    all_surfaced = {t.name for t in read_tools + write_tools}

    for blocked_name in DEFAULT_BLOCKED_TOOL_NAMES:
        assert blocked_name not in all_surfaced, (
            f"{blocked_name} must NEVER be surfaced to the agent"
        )

    # Also verify the explicit load_scope("blocked") contract.
    assert shared_manifest.load_scope("blocked", config) == []


def test_belt_and_suspenders_tool_scoped_blocked_not_in_config_blocklist():
    """A tool tagged ``@scoped_tool('blocked')`` is still blocked even if
    its name is NOT in ``MCPScopeConfig.blocked_tool_names``."""

    local = ToolManifest()

    def phantom_tool() -> str:
        return "should never run"

    local.register(phantom_tool, scope="blocked", name="phantom_tool")

    # Config with an EMPTY blocklist — the scope tag alone must block it.
    config = MCPScopeConfig(
        load_read=True,
        load_write=True,
        blocked_tool_names=[],
    )
    assert local.load_scope("read", config) == []
    assert local.load_scope("write", config) == []
    assert local.load_scope("blocked", config) == []
    assert local.load_all_allowed(config) == []

    # It IS recorded (for audit) — just never surfaced.
    assert any(t.name == "phantom_tool" for t in local.get_all_loaded())
    assert any(t.name == "phantom_tool" for t in local.get_blocked())


# ---------------------------------------------------------------------- #
# Counts
# ---------------------------------------------------------------------- #


def test_loaded_tool_count_matches_expected():
    """Verify exact counts of surfaced tools under known configs."""
    default_cfg = MCPScopeConfig()
    write_cfg = MCPScopeConfig(load_write=True)

    default_read = shared_manifest.load_scope("read", default_cfg)
    write_read = shared_manifest.load_scope("read", write_cfg)
    write_write = shared_manifest.load_scope("write", write_cfg)

    # Read tools: log_search, metric_query, runbook_lookup +
    # Layer 5 docs_*: find_docs, reconcile_docs, detect_stale_docs, check_doc_links +
    # Layer P2.2 finops: query_aws_costs, query_opencost_allocation,
    # query_kubecost_allocation, top_spenders, find_cost_anomalies.
    assert len(default_read) == 12
    assert len(write_read) == 12
    # Two write tools: slack_post, jira_create_ticket.
    assert len(write_write) == 2

    # Blocked tools registered but never loaded: terraform_apply, kubectl_delete.
    blocked_names = {t.name for t in shared_manifest.get_blocked()}
    assert "terraform_apply" in blocked_names
    assert "kubectl_delete" in blocked_names


def test_load_all_allowed_respects_config():
    read_only = {
        "log_search",
        "metric_query",
        "runbook_lookup",
        "find_docs",
        "reconcile_docs",
        "detect_stale_docs",
        "check_doc_links",
        "query_aws_costs",
        "query_opencost_allocation",
        "query_kubecost_allocation",
        "top_spenders",
        "find_cost_anomalies",
    }
    assert {
        t.name for t in shared_manifest.load_all_allowed(MCPScopeConfig())
    } == read_only
    assert {
        t.name
        for t in shared_manifest.load_all_allowed(MCPScopeConfig(load_write=True))
    } == read_only | {"slack_post", "jira_create_ticket"}


# ---------------------------------------------------------------------- #
# Decorator idempotency
# ---------------------------------------------------------------------- #


def test_decorator_reimport_is_idempotent():
    """Reimporting a tool module must not raise or double-register."""
    import importlib

    import mcp.tools.read.log_search as mod

    before = [t for t in shared_manifest.get_all_loaded() if t.name == "log_search"]
    importlib.reload(mod)
    after = [t for t in shared_manifest.get_all_loaded() if t.name == "log_search"]

    assert len(before) == 1
    assert len(after) == 1


def test_reregistering_with_different_scope_raises():
    """Re-registering the same name under a different scope must raise.

    This guards against a destructive tool being silently "promoted"
    from blocked to read via a careless import.
    """
    local = ToolManifest()

    def first() -> str:
        return "first"

    local.register(first, scope="read", name="dup_tool")
    with pytest.raises(ValueError):
        local.register(first, scope="blocked", name="dup_tool")


def test_reregistering_same_scope_is_idempotent():
    """Re-registering the same name + same scope is a safe reload."""
    local = ToolManifest()

    def v1() -> str:
        return "v1"

    def v2() -> str:
        return "v2"

    local.register(v1, scope="read", name="dup_tool")
    # Reload-equivalent: same name, same scope, new callable object.
    entry = local.register(v2, scope="read", name="dup_tool")
    assert entry.fn is v2
    # Still exactly one registration.
    matches = [t for t in local.get_all_loaded() if t.name == "dup_tool"]
    assert len(matches) == 1


def test_invalid_scope_raises():
    with pytest.raises(ValueError):
        scoped_tool("admin")(lambda: None)  # type: ignore[arg-type]
