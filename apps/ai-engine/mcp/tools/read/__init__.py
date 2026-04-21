"""Read-scope MCP tools.

Importing this package triggers registration of every read-only tool
with the ``ToolManifest``. The manifest — not this package — decides
which tools are surfaced to the agent.
"""

from mcp.tools.read import log_search, metric_query, runbook_lookup  # noqa: F401

__all__ = ["log_search", "metric_query", "runbook_lookup"]
