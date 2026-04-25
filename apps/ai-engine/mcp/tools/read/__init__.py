"""Read-scope MCP tools.

Importing this package triggers registration of every read-only tool
with the ``ToolManifest``. The manifest — not this package — decides
which tools are surfaced to the agent.
"""

from mcp.tools.read import (  # noqa: F401
    docs_find,
    docs_link_check,
    docs_reconcile,
    docs_staleness,
    log_search,
    metric_query,
    runbook_lookup,
)
from mcp.tools.read import finops  # noqa: F401

__all__ = [
    "docs_find",
    "docs_link_check",
    "docs_reconcile",
    "docs_staleness",
    "finops",
    "log_search",
    "metric_query",
    "runbook_lookup",
]
