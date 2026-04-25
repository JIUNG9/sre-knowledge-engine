"""Read-scope tool: ``query_opencost_allocation``.

Queries the OpenCost API (the CNCF project spun out of Kubecost's
open-source core). OpenCost exposes an HTTP endpoint
``/allocation/compute`` that returns Kubernetes cost allocation
grouped by namespace, controller, pod, or node.

Docs: https://www.opencost.io/docs/integrations/api
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx

from mcp.scoped_tool import scoped_tool

from .config import get_config, unavailable_response

logger = logging.getLogger("aegis.mcp.finops.opencost")

Aggregate = Literal["namespace", "controller", "pod", "node", "cluster"]


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "window": {
            "type": "string",
            "description": (
                "Query window in OpenCost duration form, "
                "e.g. '7d', '24h', '1h'."
            ),
            "default": "7d",
        },
        "aggregate": {
            "type": "string",
            "enum": ["namespace", "controller", "pod", "node", "cluster"],
            "default": "namespace",
        },
    },
}


@scoped_tool("read")
def query_opencost_allocation(
    window: str = "7d",
    aggregate: Aggregate = "namespace",
) -> dict[str, Any]:
    """Return OpenCost allocation for a window, aggregated by a dimension.

    Args:
        window: OpenCost-style duration such as ``"7d"`` or ``"24h"``.
        aggregate: Aggregation dimension.

    Returns:
        Dict with ``status``, the raw OpenCost records, and a
        normalised ``allocations`` ranked list. A ``status='unavailable'``
        response is returned when the backend URL is unset or the HTTP
        call fails.
    """
    cfg = get_config()
    endpoint = cfg.opencost_endpoint("/allocation/compute")
    if endpoint is None:
        return unavailable_response(
            tool="query_opencost_allocation",
            backend="opencost",
            reason=(
                "AEGIS_FINOPS_OPENCOST_URL is not set — OpenCost backend "
                "is not configured"
            ),
        )

    params = {
        "window": window,
        "aggregate": aggregate,
        "accumulate": "true",
    }

    try:
        with httpx.Client(timeout=cfg.http_timeout_s) as client:
            resp = client.get(endpoint, params=params)
    except httpx.RequestError as exc:
        logger.warning("opencost: request failed: %s", exc)
        return unavailable_response(
            tool="query_opencost_allocation",
            backend="opencost",
            reason=f"OpenCost request failed: {exc}",
            extra={"endpoint": endpoint},
        )

    if resp.status_code >= 400:
        return unavailable_response(
            tool="query_opencost_allocation",
            backend="opencost",
            reason=f"OpenCost HTTP {resp.status_code}: {resp.text[:200]}",
            extra={"endpoint": endpoint, "http_status": resp.status_code},
        )

    try:
        body = resp.json()
    except ValueError as exc:
        return unavailable_response(
            tool="query_opencost_allocation",
            backend="opencost",
            reason=f"OpenCost returned non-JSON: {exc}",
        )

    allocations = _normalise_opencost(body)
    total = round(sum(a["total_cost"] for a in allocations), 4)

    return {
        "status": "success",
        "tool": "query_opencost_allocation",
        "backend": "opencost",
        "endpoint": endpoint,
        "window": window,
        "aggregate": aggregate,
        "currency": "USD",
        "total_cost": total,
        "allocations": allocations,
        "raw_record_count": len(allocations),
    }


def _normalise_opencost(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten OpenCost's `data` array-of-maps into a ranked list.

    OpenCost returns ``{"code": 200, "data": [{ name: { ...cost breakdown... } }]}``.
    When ``accumulate=true`` the array has a single entry whose keys are
    the aggregated dimensions.
    """
    data = body.get("data") or []
    allocations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in data:
        if not isinstance(bucket, dict):
            continue
        for name, entry in bucket.items():
            if name in seen or not isinstance(entry, dict):
                continue
            seen.add(name)
            total = _sum_cost_fields(entry)
            allocations.append(
                {
                    "name": name,
                    "cpu_cost": _as_float(entry.get("cpuCost")),
                    "gpu_cost": _as_float(entry.get("gpuCost")),
                    "ram_cost": _as_float(entry.get("ramCost")),
                    "pv_cost": _as_float(entry.get("pvCost")),
                    "network_cost": _as_float(entry.get("networkCost")),
                    "shared_cost": _as_float(entry.get("sharedCost")),
                    "total_cost": round(total, 4),
                }
            )
    allocations.sort(key=lambda a: -a["total_cost"])
    return allocations


def _sum_cost_fields(entry: dict[str, Any]) -> float:
    return sum(
        _as_float(entry.get(key))
        for key in (
            "cpuCost",
            "gpuCost",
            "ramCost",
            "pvCost",
            "networkCost",
            "sharedCost",
        )
    )


def _as_float(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


query_opencost_allocation.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["query_opencost_allocation", "INPUT_SCHEMA"]
