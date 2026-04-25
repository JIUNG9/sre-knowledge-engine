"""Read-scope tool: ``query_aws_costs``.

Thin wrapper around `boto3.client('ce').get_cost_and_usage`. Returns a
JSON-serialisable dict shaped for agent consumption. boto3 is an
optional dependency (``pip install aegis-ai-engine[finops]``) — if it
is not importable we return a 503-style ``unavailable`` payload
instead of crashing.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from mcp.scoped_tool import scoped_tool

from .config import get_config, unavailable_response

logger = logging.getLogger("aegis.mcp.finops.aws_cost_explorer")

try:  # pragma: no cover - import guard
    import boto3  # type: ignore[import-not-found]
    from botocore.exceptions import (  # type: ignore[import-not-found]
        BotoCoreError,
        ClientError,
        NoCredentialsError,
    )

    _HAS_BOTO3 = True
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]
    BotoCoreError = Exception  # type: ignore[assignment,misc]
    ClientError = Exception  # type: ignore[assignment,misc]
    NoCredentialsError = Exception  # type: ignore[assignment,misc]
    _HAS_BOTO3 = False


Granularity = Literal["DAILY", "MONTHLY", "HOURLY"]


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "ISO date (YYYY-MM-DD), inclusive. Required.",
        },
        "end_date": {
            "type": "string",
            "description": "ISO date (YYYY-MM-DD), exclusive. Required.",
        },
        "service": {
            "type": "string",
            "description": (
                "Optional AWS service filter "
                "(e.g. 'Amazon Elastic Compute Cloud - Compute')."
            ),
        },
        "granularity": {
            "type": "string",
            "enum": ["DAILY", "MONTHLY", "HOURLY"],
            "default": "DAILY",
        },
        "group_by": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional list of Cost Explorer GroupBy dimensions, "
                "e.g. ['SERVICE'], ['LINKED_ACCOUNT', 'SERVICE']."
            ),
        },
    },
    "required": ["start_date", "end_date"],
}


@scoped_tool("read")
def query_aws_costs(
    start_date: str,
    end_date: str,
    service: str | None = None,
    granularity: Granularity = "DAILY",
    group_by: list[str] | None = None,
) -> dict[str, Any]:
    """Query AWS Cost Explorer for unblended costs in a date window.

    Args:
        start_date: Inclusive start date (``YYYY-MM-DD``).
        end_date: Exclusive end date (``YYYY-MM-DD``).
        service: Optional AWS service name to filter by.
        granularity: ``"DAILY"``, ``"MONTHLY"`` or ``"HOURLY"``.
        group_by: Optional list of dimensions to group on
            (e.g. ``["SERVICE"]``).

    Returns:
        Dict with ``status`` plus normalised ``results``. When the
        backend is not available (no boto3, no credentials, client
        error), a ``status='unavailable'`` dict is returned — the
        caller is expected to gracefully degrade.
    """
    if not _HAS_BOTO3:
        return unavailable_response(
            tool="query_aws_costs",
            backend="aws_cost_explorer",
            reason="boto3 is not installed — install the 'finops' extra",
            extra={"install_hint": "pip install aegis-ai-engine[finops]"},
        )

    cfg = get_config()
    try:
        session_kwargs: dict[str, Any] = {"region_name": cfg.aws_region}
        if cfg.aws_profile:
            session_kwargs["profile_name"] = cfg.aws_profile
        session = boto3.Session(**session_kwargs)  # type: ignore[union-attr]
        client = session.client("ce")

        request: dict[str, Any] = {
            "TimePeriod": {"Start": start_date, "End": end_date},
            "Granularity": granularity,
            "Metrics": ["UnblendedCost"],
        }
        if group_by:
            request["GroupBy"] = [
                {"Type": "DIMENSION", "Key": dim.upper()} for dim in group_by
            ]
        if service:
            request["Filter"] = {
                "Dimensions": {"Key": "SERVICE", "Values": [service]}
            }

        response = client.get_cost_and_usage(**request)
    except NoCredentialsError as exc:  # type: ignore[misc]
        logger.warning("aws_cost_explorer: no credentials: %s", exc)
        return unavailable_response(
            tool="query_aws_costs",
            backend="aws_cost_explorer",
            reason=f"no AWS credentials available: {exc}",
        )
    except (BotoCoreError, ClientError) as exc:  # type: ignore[misc]
        logger.warning("aws_cost_explorer: client error: %s", exc)
        return unavailable_response(
            tool="query_aws_costs",
            backend="aws_cost_explorer",
            reason=f"Cost Explorer error: {exc}",
        )
    except Exception as exc:
        logger.exception("aws_cost_explorer: unexpected failure")
        return unavailable_response(
            tool="query_aws_costs",
            backend="aws_cost_explorer",
            reason=f"unexpected failure: {exc}",
        )

    results_by_time = response.get("ResultsByTime", []) or []
    normalised: list[dict[str, Any]] = []
    total = 0.0
    currency = "USD"

    for period in results_by_time:
        time_period = period.get("TimePeriod", {}) or {}
        period_start = time_period.get("Start", "")
        period_end = time_period.get("End", "")
        groups = period.get("Groups") or []

        if groups:
            for group in groups:
                keys = group.get("Keys", []) or []
                metrics = group.get("Metrics", {}) or {}
                unblended = metrics.get("UnblendedCost", {}) or {}
                amount = _safe_float(unblended.get("Amount"))
                currency = unblended.get("Unit", currency) or currency
                total += amount
                normalised.append(
                    {
                        "start": period_start,
                        "end": period_end,
                        "keys": keys,
                        "amount": amount,
                        "currency": currency,
                    }
                )
        else:
            totals = period.get("Total", {}) or {}
            unblended = totals.get("UnblendedCost", {}) or {}
            amount = _safe_float(unblended.get("Amount"))
            currency = unblended.get("Unit", currency) or currency
            total += amount
            normalised.append(
                {
                    "start": period_start,
                    "end": period_end,
                    "keys": [],
                    "amount": amount,
                    "currency": currency,
                }
            )

    return {
        "status": "success",
        "tool": "query_aws_costs",
        "backend": "aws_cost_explorer",
        "region": cfg.aws_region,
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "service_filter": service,
        "group_by": group_by or [],
        "currency": currency,
        "total_cost": round(total, 4),
        "period_count": len(normalised),
        "results": normalised,
    }


def _safe_float(value: Any) -> float:
    """Cost Explorer returns stringified decimals; coerce to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


query_aws_costs.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["query_aws_costs", "INPUT_SCHEMA"]
