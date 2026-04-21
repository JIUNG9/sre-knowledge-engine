"""Read-scope tool: runbook_lookup.

Looks up matching runbook entries. Read-only.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("read")
def runbook_lookup(query: str, limit: int = 5) -> dict:
    """Search the runbook knowledge base.

    Skeleton implementation.
    """
    return {
        "status": "success",
        "tool": "runbook_lookup",
        "query": query,
        "limit": limit,
        "results": [],
    }


__all__ = ["runbook_lookup"]
