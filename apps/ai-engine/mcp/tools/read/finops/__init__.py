"""Aegis FinOps MCP tool suite (Phase 2.2).

Importing this package triggers registration of every read-only
FinOps tool with the global :class:`~mcp.manifest.ToolManifest`.

Tools exposed
-------------

- ``query_aws_costs``           AWS Cost Explorer (boto3).
- ``query_opencost_allocation`` OpenCost HTTP API (Kubernetes).
- ``query_kubecost_allocation`` Kubecost HTTP API (Kubernetes).
- ``top_spenders``              Composite — ranks top cost drivers
  across every configured backend.
- ``find_cost_anomalies``       Z-score anomaly detector over a
  daily cost series.

Every tool is registered with ``@scoped_tool("read")``, so the
manifest exposes them in the read bucket and they never reach the
write bucket. All tools return JSON-serialisable Python dicts.
"""

from __future__ import annotations

from .anomaly_detect import find_cost_anomalies
from .aws_cost_explorer import query_aws_costs
from .config import (
    FinOpsConfig,
    get_config,
    reset_config,
    set_config,
    unavailable_response,
)
from .kubecost import query_kubecost_allocation
from .opencost import query_opencost_allocation
from .top_spenders import top_spenders

__all__ = [
    # Tools
    "query_aws_costs",
    "query_opencost_allocation",
    "query_kubecost_allocation",
    "top_spenders",
    "find_cost_anomalies",
    # Config
    "FinOpsConfig",
    "get_config",
    "set_config",
    "reset_config",
    "unavailable_response",
]
