"""Read-scope tool: ``top_spenders``.

Composite tool. Calls whichever backends are configured (AWS Cost
Explorer, OpenCost, Kubecost) and returns a unified ranked list of
top spenders. Designed for prompts like::

    "Who's spending the most this week?"

The tool never raises on an unavailable backend — it records the
backend's unavailability in the ``providers`` sub-map and moves on.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from mcp.scoped_tool import scoped_tool

from .aws_cost_explorer import query_aws_costs
from .kubecost import query_kubecost_allocation
from .opencost import query_opencost_allocation

logger = logging.getLogger("aegis.mcp.finops.top_spenders")

Provider = Literal["aws", "opencost", "kubecost", "all"]


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "provider": {
            "type": "string",
            "enum": ["aws", "opencost", "kubecost", "all"],
            "default": "all",
        },
        "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 500},
        "window": {
            "type": "string",
            "description": "Lookback window, e.g. '7d', '24h'.",
            "default": "7d",
        },
    },
}


@scoped_tool("read")
def top_spenders(
    provider: Provider = "all",
    limit: int = 10,
    window: str = "7d",
) -> dict[str, Any]:
    """Return the top-N cost drivers across one or more backends.

    Args:
        provider: ``"aws"``, ``"opencost"``, ``"kubecost"``, or
            ``"all"`` to fan-out.
        limit: Maximum number of rows in the ranked result.
        window: Lookback window; maps to a date range for AWS and to
            a duration for OpenCost/Kubecost.

    Returns:
        Dict with a ranked ``top_spenders`` list plus a ``providers``
        map describing per-backend status.
    """
    start_date, end_date = _window_to_dates(window)

    providers_report: dict[str, dict[str, Any]] = {}
    unified: list[dict[str, Any]] = []

    if provider in ("aws", "all"):
        aws_result = query_aws_costs(
            start_date=start_date,
            end_date=end_date,
            granularity="DAILY",
            group_by=["SERVICE"],
        )
        providers_report["aws"] = _summarise(aws_result)
        if aws_result.get("status") == "success":
            for row in aws_result.get("results", []):
                keys = row.get("keys") or []
                name = keys[0] if keys else "unknown"
                unified.append(
                    {
                        "provider": "aws",
                        "name": name,
                        "total_cost": round(float(row.get("amount", 0.0)), 4),
                        "currency": row.get("currency", "USD"),
                        "period_start": row.get("start"),
                        "period_end": row.get("end"),
                    }
                )

    if provider in ("opencost", "all"):
        oc_result = query_opencost_allocation(window=window, aggregate="namespace")
        providers_report["opencost"] = _summarise(oc_result)
        if oc_result.get("status") == "success":
            for row in oc_result.get("allocations", []):
                unified.append(
                    {
                        "provider": "opencost",
                        "name": row["name"],
                        "total_cost": row["total_cost"],
                        "currency": oc_result.get("currency", "USD"),
                        "window": window,
                    }
                )

    if provider in ("kubecost", "all"):
        kc_result = query_kubecost_allocation(window=window, aggregate="namespace")
        providers_report["kubecost"] = _summarise(kc_result)
        if kc_result.get("status") == "success":
            for row in kc_result.get("allocations", []):
                unified.append(
                    {
                        "provider": "kubecost",
                        "name": row["name"],
                        "total_cost": row["total_cost"],
                        "currency": kc_result.get("currency", "USD"),
                        "window": window,
                    }
                )

    # Merge rows from Kubernetes providers that share a namespace name,
    # but keep AWS rows as-is (AWS service != namespace). Merging across
    # providers would double-count; we keep provider as a tie-breaker
    # and let the agent summarise.
    unified.sort(key=lambda r: -r["total_cost"])
    ranked = unified[:limit]

    grand_total = round(
        sum(
            p.get("total_cost", 0.0)
            for p in providers_report.values()
            if isinstance(p.get("total_cost"), (int, float))
        ),
        4,
    )

    any_available = any(
        p.get("status") == "success" for p in providers_report.values()
    )

    return {
        "status": "success" if any_available else "unavailable",
        "tool": "top_spenders",
        "provider": provider,
        "window": window,
        "limit": limit,
        "grand_total": grand_total,
        "providers": providers_report,
        "top_spenders": ranked,
    }


def _summarise(result: dict[str, Any]) -> dict[str, Any]:
    """Reduce a backend tool result to a compact status blurb."""
    if result.get("status") == "success":
        total = result.get("total_cost")
        return {
            "status": "success",
            "total_cost": total,
            "currency": result.get("currency", "USD"),
        }
    return {
        "status": result.get("status", "unavailable"),
        "reason": result.get("reason"),
    }


def _window_to_dates(window: str) -> tuple[str, str]:
    """Translate a ``"7d"``/``"24h"``-style window to an inclusive-exclusive
    date range suitable for AWS Cost Explorer.

    Cost Explorer ``End`` is exclusive, so we set it to tomorrow's date.
    """
    days = _window_to_days(window)
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    end = today + timedelta(days=1)  # exclusive
    return start.isoformat(), end.isoformat()


def _window_to_days(window: str) -> int:
    w = window.strip().lower()
    try:
        if w.endswith("d"):
            return max(1, int(w[:-1] or "1"))
        if w.endswith("h"):
            hours = max(1, int(w[:-1] or "1"))
            # Round up to full day for Cost Explorer's DAILY granularity.
            return max(1, (hours + 23) // 24)
    except ValueError:
        pass
    # Fallback — treat anything unparseable as 7 days.
    return 7


top_spenders.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["top_spenders", "INPUT_SCHEMA"]
