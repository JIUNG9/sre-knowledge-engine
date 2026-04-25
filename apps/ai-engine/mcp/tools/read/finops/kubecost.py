"""Read-scope tool: ``query_kubecost_allocation``.

Queries the Kubecost Cost Analyzer API. Kubecost's
``/model/allocation`` endpoint returns an allocation tree shaped
similarly to OpenCost (which is Kubecost's open-source core), but
the response envelope differs enough to warrant a dedicated tool.

Docs: https://docs.kubecost.com/apis/apis-overview/allocation
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from mcp.scoped_tool import scoped_tool

from .config import get_config, unavailable_response

logger = logging.getLogger("aegis.mcp.finops.kubecost")


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "window": {
            "type": "string",
            "description": (
                "Query window in Kubecost duration form, "
                "e.g. '7d', '24h', '1h'."
            ),
            "default": "7d",
        },
        "aggregate": {
            "type": "string",
            "description": (
                "Aggregation dimension. Kubecost supports a superset of "
                "OpenCost — common values are 'namespace', 'controller', "
                "'label:team', 'cluster'."
            ),
            "default": "namespace",
        },
    },
}


@scoped_tool("read")
def query_kubecost_allocation(
    window: str = "7d",
    aggregate: str = "namespace",
) -> dict[str, Any]:
    """Return Kubecost allocation for a window, aggregated by a dimension.

    Args:
        window: Kubecost-style duration such as ``"7d"`` or ``"24h"``.
        aggregate: Aggregation dimension (namespace, controller,
            label:team, cluster, ...).

    Returns:
        Normalised dict with ``allocations`` ranked by total cost, or
        a ``status='unavailable'`` envelope when the backend is not
        reachable.
    """
    cfg = get_config()
    endpoint = cfg.kubecost_endpoint("/model/allocation")
    if endpoint is None:
        return unavailable_response(
            tool="query_kubecost_allocation",
            backend="kubecost",
            reason=(
                "AEGIS_FINOPS_KUBECOST_URL is not set — Kubecost backend "
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
        logger.warning("kubecost: request failed: %s", exc)
        return unavailable_response(
            tool="query_kubecost_allocation",
            backend="kubecost",
            reason=f"Kubecost request failed: {exc}",
            extra={"endpoint": endpoint},
        )

    if resp.status_code >= 400:
        return unavailable_response(
            tool="query_kubecost_allocation",
            backend="kubecost",
            reason=f"Kubecost HTTP {resp.status_code}: {resp.text[:200]}",
            extra={"endpoint": endpoint, "http_status": resp.status_code},
        )

    try:
        body = resp.json()
    except ValueError as exc:
        return unavailable_response(
            tool="query_kubecost_allocation",
            backend="kubecost",
            reason=f"Kubecost returned non-JSON: {exc}",
        )

    allocations = _normalise_kubecost(body)
    total = round(sum(a["total_cost"] for a in allocations), 4)

    return {
        "status": "success",
        "tool": "query_kubecost_allocation",
        "backend": "kubecost",
        "endpoint": endpoint,
        "window": window,
        "aggregate": aggregate,
        "currency": "USD",
        "total_cost": total,
        "allocations": allocations,
        "raw_record_count": len(allocations),
    }


def _normalise_kubecost(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten Kubecost's `data` entries into ranked allocations.

    Kubecost returns ``{"code": 200, "data": [{ name: { ...breakdown... } }]}``
    for the accumulated case, matching OpenCost closely enough that we
    can reuse the same normalisation shape.
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


query_kubecost_allocation.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["query_kubecost_allocation", "INPUT_SCHEMA"]
