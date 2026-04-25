"""Read-scope tool: ``find_cost_anomalies``.

Pulls a daily cost series from one backend and flags points whose
z-score (vs. the prior rolling window) exceeds a configurable
sensitivity threshold. No LLM required for the primary signal —
this is a deterministic detector so it stays cheap and reproducible.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from mcp.scoped_tool import scoped_tool

from .aws_cost_explorer import query_aws_costs
from .kubecost import query_kubecost_allocation
from .opencost import query_opencost_allocation

logger = logging.getLogger("aegis.mcp.finops.anomaly_detect")

Provider = Literal["aws", "opencost", "kubecost"]


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "provider": {
            "type": "string",
            "enum": ["aws", "opencost", "kubecost"],
            "default": "aws",
        },
        "lookback_days": {
            "type": "integer",
            "default": 30,
            "minimum": 7,
            "maximum": 365,
        },
        "sensitivity": {
            "type": "number",
            "description": (
                "Z-score threshold. 2.0 ~ 95th percentile, 3.0 ~ 99.7th. "
                "Lower = more sensitive (more anomalies reported)."
            ),
            "default": 2.0,
            "minimum": 0.5,
            "maximum": 6.0,
        },
    },
}


@scoped_tool("read")
def find_cost_anomalies(
    provider: Provider = "aws",
    lookback_days: int = 30,
    sensitivity: float = 2.0,
) -> dict[str, Any]:
    """Return cost spikes whose z-score exceeds the ``sensitivity`` cutoff.

    Args:
        provider: Which backend to sample.
        lookback_days: How many days of history to analyse.
        sensitivity: Z-score threshold above which a day is flagged.

    Returns:
        Dict with ``anomalies`` (list of flagged dates/amounts) and
        the daily ``series`` used for the calculation.
    """
    series = _collect_series(provider, lookback_days)
    if isinstance(series, dict) and series.get("status") == "unavailable":
        return {
            "status": "unavailable",
            "tool": "find_cost_anomalies",
            "provider": provider,
            "reason": series.get("reason", "backend unavailable"),
        }
    assert isinstance(series, list)

    if len(series) < 4:
        return {
            "status": "success",
            "tool": "find_cost_anomalies",
            "provider": provider,
            "lookback_days": lookback_days,
            "sensitivity": sensitivity,
            "series": series,
            "anomalies": [],
            "note": "not enough data points for meaningful z-score",
        }

    anomalies = _zscore_anomalies(series, sensitivity)

    return {
        "status": "success",
        "tool": "find_cost_anomalies",
        "provider": provider,
        "lookback_days": lookback_days,
        "sensitivity": sensitivity,
        "series": series,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
    }


def _collect_series(
    provider: Provider,
    lookback_days: int,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Return a ``[{date, amount}]`` daily series, or an unavailable dict."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=lookback_days)
    end = today + timedelta(days=1)

    if provider == "aws":
        result = query_aws_costs(
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            granularity="DAILY",
        )
        if result.get("status") != "success":
            return result
        return [
            {"date": row["start"], "amount": float(row.get("amount", 0.0))}
            for row in result.get("results", [])
        ]

    if provider == "opencost":
        # OpenCost's accumulate=true returns one row; we use many
        # single-day windows instead so we get a daily series.
        return _per_day_series(
            lambda day_start, day_end: query_opencost_allocation(
                window=f"{day_start}T00:00:00Z,{day_end}T00:00:00Z",
                aggregate="cluster",
            ),
            start,
            today,
        )

    if provider == "kubecost":
        return _per_day_series(
            lambda day_start, day_end: query_kubecost_allocation(
                window=f"{day_start}T00:00:00Z,{day_end}T00:00:00Z",
                aggregate="cluster",
            ),
            start,
            today,
        )

    return {
        "status": "unavailable",
        "reason": f"unknown provider: {provider}",
    }


def _per_day_series(
    fetch_day,
    start,
    today,
) -> list[dict[str, Any]] | dict[str, Any]:
    series: list[dict[str, Any]] = []
    day = start
    first_unavailable_reason: str | None = None
    while day < today:
        next_day = day + timedelta(days=1)
        result = fetch_day(day.isoformat(), next_day.isoformat())
        if result.get("status") != "success":
            if first_unavailable_reason is None:
                first_unavailable_reason = str(result.get("reason", "unavailable"))
            day = next_day
            continue
        series.append(
            {
                "date": day.isoformat(),
                "amount": float(result.get("total_cost", 0.0)),
            }
        )
        day = next_day
    if not series and first_unavailable_reason is not None:
        return {"status": "unavailable", "reason": first_unavailable_reason}
    return series


def _zscore_anomalies(
    series: list[dict[str, Any]],
    sensitivity: float,
) -> list[dict[str, Any]]:
    """Flag points where ``(x - mean) / stdev >= sensitivity``.

    We use the entire series as the reference distribution for
    simplicity — lookback_days already scopes it. A production
    implementation would use a rolling window; this is the MVP.
    """
    amounts = [pt["amount"] for pt in series]
    if len(amounts) < 2:
        return []
    mean = statistics.fmean(amounts)
    try:
        stdev = statistics.stdev(amounts)
    except statistics.StatisticsError:
        return []
    if stdev == 0:
        return []

    anomalies: list[dict[str, Any]] = []
    for pt in series:
        z = (pt["amount"] - mean) / stdev
        if z >= sensitivity:
            anomalies.append(
                {
                    "date": pt["date"],
                    "amount": round(pt["amount"], 4),
                    "z_score": round(z, 3),
                    "baseline_mean": round(mean, 4),
                    "baseline_stdev": round(stdev, 4),
                }
            )
    # Most severe first.
    anomalies.sort(key=lambda a: -a["z_score"])
    return anomalies


find_cost_anomalies.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["find_cost_anomalies", "INPUT_SCHEMA"]
