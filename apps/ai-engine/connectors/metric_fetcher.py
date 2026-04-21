"""PromQL metric queries against SigNoz ``/api/v1/query_range``.

SigNoz exposes a Prometheus-compatible query endpoint for both instant
and range queries. We target the range endpoint for both: instant
queries use ``start == end``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from connectors.models import MetricPoint, MetricSeries, MetricSeriesRow
from connectors.signoz_client import SigNozClient


logger = logging.getLogger("aegis.connectors.metrics")


_RANGE_PATH = "/api/v1/query_range"


class MetricFetcher:
    """PromQL wrapper. Returns normalised :class:`MetricSeries` objects."""

    def __init__(self, client: SigNozClient) -> None:
        self._client = client

    async def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step_seconds: int,
    ) -> MetricSeries:
        """Execute a PromQL range query.

        Args:
            promql: Full PromQL expression.
            start: Inclusive lower bound.
            end: Inclusive upper bound.
            step_seconds: Resolution of the returned series.
        """
        if step_seconds <= 0:
            raise ValueError("step_seconds must be positive")
        if end < start:
            raise ValueError("end must be >= start")

        params = {
            "query": promql,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": step_seconds,
        }
        payload = await self._client.get(_RANGE_PATH, params=params)
        series = _parse_series(payload)

        logger.info(
            "metric_fetcher.query_range promql=%r series=%d step=%ds",
            promql,
            len(series),
            step_seconds,
        )
        return MetricSeries(
            promql=promql,
            start=start,
            end=end,
            step_seconds=step_seconds,
            series=series,
        )

    async def query_instant(
        self,
        promql: str,
        at: datetime,
    ) -> MetricPoint:
        """Execute a single-point instant query.

        Implemented as a 1-step range query so we hit the same endpoint
        as :meth:`query_range`, avoiding divergent error paths.
        """
        result = await self.query_range(
            promql, start=at, end=at, step_seconds=1
        )
        for row in result.series:
            if row.points:
                return row.points[-1]

        # Empty result — still return a deterministic point so callers
        # don't need a None-check. Zero-value with empty labels.
        return MetricPoint(timestamp=at, value=float("nan"), labels={})


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _parse_series(payload: Any) -> list[MetricSeriesRow]:
    """Extract series rows from a Prometheus/SigNoz response shape.

    Prometheus shape::

        {"status": "success",
         "data": {"resultType": "matrix",
                  "result": [{"metric": {...}, "values": [[ts, "v"], ...]}]}}

    SigNoz sometimes wraps this into ``{"data": {"result": [...]}}`` or
    emits ``{"result": [{"series": [...]}]}`` for its internal engine.
    """
    if not isinstance(payload, dict):
        return []

    # Prometheus path.
    data = payload.get("data")
    if isinstance(data, dict):
        result = data.get("result")
        if isinstance(result, list):
            return [_parse_prom_row(r) for r in result if isinstance(r, dict)]

    # SigNoz native path.
    result = payload.get("result")
    if isinstance(result, list):
        rows: list[MetricSeriesRow] = []
        for entry in result:
            if not isinstance(entry, dict):
                continue
            for s in entry.get("series", []) or []:
                if isinstance(s, dict):
                    rows.append(_parse_signoz_row(s))
        if rows:
            return rows

    return []


def _parse_prom_row(row: dict) -> MetricSeriesRow:
    labels = row.get("metric") or {}
    pairs = row.get("values") or []
    if not pairs and "value" in row:
        pairs = [row["value"]]

    points: list[MetricPoint] = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        ts_raw, val_raw = pair[0], pair[1]
        try:
            ts = datetime.fromtimestamp(float(ts_raw))
            val = float(val_raw)
        except (TypeError, ValueError):
            continue
        points.append(MetricPoint(timestamp=ts, value=val, labels=dict(labels)))

    return MetricSeriesRow(
        labels={str(k): str(v) for k, v in labels.items()},
        points=points,
    )


def _parse_signoz_row(row: dict) -> MetricSeriesRow:
    labels = row.get("labels") or row.get("metric") or {}
    points_raw = row.get("values") or row.get("points") or []

    points: list[MetricPoint] = []
    for p in points_raw:
        ts_raw: Any
        val_raw: Any
        if isinstance(p, dict):
            ts_raw = p.get("timestamp") or p.get("ts")
            val_raw = p.get("value") or p.get("v")
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            ts_raw, val_raw = p[0], p[1]
        else:
            continue

        try:
            if isinstance(ts_raw, (int, float)) and ts_raw > 1e12:
                ts = datetime.fromtimestamp(ts_raw / 1000.0)
            else:
                ts = datetime.fromtimestamp(float(ts_raw))
            val = float(val_raw)
        except (TypeError, ValueError):
            continue

        points.append(MetricPoint(timestamp=ts, value=val, labels=dict(labels)))

    return MetricSeriesRow(
        labels={str(k): str(v) for k, v in labels.items()},
        points=points,
    )
