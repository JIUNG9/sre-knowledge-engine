"""Read-scope tool: metric_query.

Queries time-series metrics (Prometheus/SigNoz). Read-only.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("read")
def metric_query(service: str, metric_name: str = "", time_range: str = "1h") -> dict:
    """Query time-series metrics for a service.

    Skeleton implementation.
    """
    return {
        "status": "success",
        "tool": "metric_query",
        "service": service,
        "metric_name": metric_name,
        "time_range": time_range,
        "series": [],
    }


__all__ = ["metric_query"]
