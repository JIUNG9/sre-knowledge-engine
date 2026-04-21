"""Read-scope tool: log_search.

Queries the centralized log store. Read-only; no side effects.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("read")
def log_search(service: str, query: str = "", time_range: str = "1h") -> dict:
    """Search logs for a given service.

    Skeleton implementation. Returns a placeholder result shaped like
    the production response so downstream agents can develop against it.
    """
    return {
        "status": "success",
        "tool": "log_search",
        "service": service,
        "query": query,
        "time_range": time_range,
        "entries": [],
    }


__all__ = ["log_search"]
