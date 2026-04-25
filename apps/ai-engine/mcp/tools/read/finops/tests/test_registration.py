"""Manifest-registration tests for the Phase 2.2 FinOps tools.

Verifies the same invariants the project uses for every new
``@scoped_tool("read")`` surface:

1. Each finops tool appears in ``load_scope("read")``.
2. No finops tool appears in ``load_scope("write")`` or
   ``load_scope("blocked")`` — even when ``load_write=True``.
3. ``get_blocked()`` does not contain any finops tool name.
"""

from __future__ import annotations

# Importing the read package triggers decorator registration.
import mcp.tools.read  # noqa: F401
from mcp.manifest import manifest as shared_manifest
from mcp.scope_config import MCPScopeConfig


FINOPS_TOOL_NAMES = {
    "query_aws_costs",
    "query_opencost_allocation",
    "query_kubecost_allocation",
    "top_spenders",
    "find_cost_anomalies",
}


def test_every_finops_tool_is_registered_as_read():
    config = MCPScopeConfig()
    read_names = {t.name for t in shared_manifest.load_scope("read", config)}
    missing = FINOPS_TOOL_NAMES - read_names
    assert missing == set(), f"missing from read scope: {missing}"


def test_no_finops_tool_leaks_into_write_scope():
    config = MCPScopeConfig(load_write=True)
    write_names = {t.name for t in shared_manifest.load_scope("write", config)}
    leaked = FINOPS_TOOL_NAMES & write_names
    assert leaked == set(), f"finops tools leaked into write scope: {leaked}"


def test_no_finops_tool_ever_blocked():
    assert shared_manifest.load_scope("blocked", MCPScopeConfig()) == []
    blocked_names = {t.name for t in shared_manifest.get_blocked()}
    leaked = FINOPS_TOOL_NAMES & blocked_names
    assert leaked == set(), f"finops tools incorrectly registered as blocked: {leaked}"


def test_finops_tools_expose_callable_entries():
    config = MCPScopeConfig()
    read = {t.name: t for t in shared_manifest.load_scope("read", config)}
    for name in FINOPS_TOOL_NAMES:
        assert callable(read[name].fn)
