"""Trace lookups and filtered search against SigNoz ``/api/v1/traces``.

Two operations are exposed:

* :meth:`TraceFetcher.get_trace` — fetch one trace (+ its spans) by id.
* :meth:`TraceFetcher.search`    — list recent traces, filterable by
  service, operation, and minimum duration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from connectors.models import Trace, TraceSpan, TraceSummary
from connectors.signoz_client import SigNozClient


logger = logging.getLogger("aegis.connectors.traces")


_TRACES_PATH = "/api/v1/traces"


class TraceFetcher:
    """Trace inspection and search."""

    def __init__(self, client: SigNozClient) -> None:
        self._client = client

    async def get_trace(self, trace_id: str) -> Trace:
        """Fetch a single trace and its spans by ``trace_id``."""
        if not trace_id:
            raise ValueError("trace_id must be non-empty")

        payload = await self._client.get(f"{_TRACES_PATH}/{trace_id}")
        return _parse_trace(payload, fallback_trace_id=trace_id)

    async def search(
        self,
        service: str | None,
        operation: str | None,
        min_duration_ms: int | None,
        start: datetime,
        end: datetime,
    ) -> list[TraceSummary]:
        """List recent traces matching the given filters."""
        if end <= start:
            raise ValueError("end must be after start")

        params: dict[str, Any] = {
            "start": int(start.timestamp() * 1_000_000_000),
            "end": int(end.timestamp() * 1_000_000_000),
        }
        if service:
            params["service"] = service
        if operation:
            params["operation"] = operation
        if min_duration_ms is not None:
            if min_duration_ms < 0:
                raise ValueError("min_duration_ms must be >= 0")
            params["minDuration"] = min_duration_ms

        payload = await self._client.get(_TRACES_PATH, params=params)
        summaries = _parse_summaries(payload)

        logger.info(
            "trace_fetcher.search service=%s operation=%s min_duration_ms=%s "
            "returned=%d",
            service,
            operation,
            min_duration_ms,
            len(summaries),
        )
        return summaries


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _parse_trace(payload: Any, fallback_trace_id: str) -> Trace:
    """Parse SigNoz trace-detail payload."""
    if not isinstance(payload, dict):
        raise ValueError("trace payload was not an object")

    data = payload.get("data") if "data" in payload else payload
    if not isinstance(data, dict):
        data = {}

    trace_id = data.get("traceId") or data.get("trace_id") or fallback_trace_id
    spans_raw = data.get("spans") or data.get("events") or []
    spans = [_parse_span(s) for s in spans_raw if isinstance(s, dict)]

    start_time = (
        _parse_ts(data.get("startTime") or data.get("start_time"))
        or (min((s.start_time for s in spans), default=datetime.fromtimestamp(0)))
    )
    duration = float(
        data.get("durationMs")
        or data.get("duration_ms")
        or (max((s.duration_ms for s in spans), default=0.0))
    )

    return Trace(
        trace_id=trace_id,
        root_service=data.get("rootService") or data.get("root_service"),
        root_operation=data.get("rootOperation") or data.get("root_operation"),
        start_time=start_time,
        duration_ms=duration,
        spans=spans,
    )


def _parse_span(raw: dict) -> TraceSpan:
    start = _parse_ts(raw.get("startTime") or raw.get("start_time")) or datetime.fromtimestamp(0)
    duration = float(raw.get("durationMs") or raw.get("duration_ms") or 0.0)
    return TraceSpan(
        span_id=str(raw.get("spanId") or raw.get("span_id") or ""),
        parent_span_id=raw.get("parentSpanId") or raw.get("parent_span_id"),
        name=str(raw.get("name") or raw.get("operation") or ""),
        service=str(raw.get("serviceName") or raw.get("service") or ""),
        start_time=start,
        duration_ms=duration,
        status_code=raw.get("statusCode") or raw.get("status_code"),
        attributes=raw.get("attributes") or {},
    )


def _parse_summaries(payload: Any) -> list[TraceSummary]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") if "data" in payload else payload

    rows: list[Any] = []
    if isinstance(data, dict):
        rows = data.get("traces") or data.get("items") or []
    elif isinstance(data, list):
        rows = data

    summaries: list[TraceSummary] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        start = _parse_ts(row.get("startTime") or row.get("start_time"))
        if start is None:
            continue
        summaries.append(
            TraceSummary(
                trace_id=str(row.get("traceId") or row.get("trace_id") or ""),
                service=str(row.get("serviceName") or row.get("service") or ""),
                operation=str(row.get("operation") or row.get("name") or ""),
                start_time=start,
                duration_ms=float(row.get("durationMs") or row.get("duration_ms") or 0.0),
                status_code=row.get("statusCode") or row.get("status_code"),
                span_count=int(row.get("spanCount") or row.get("span_count") or 0),
            )
        )
    return summaries


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # ns → s heuristic identical to log_fetcher.
        if value > 1e17:
            return datetime.fromtimestamp(value / 1_000_000_000)
        if value > 1e14:
            return datetime.fromtimestamp(value / 1_000_000)
        if value > 1e11:
            return datetime.fromtimestamp(value / 1_000)
        return datetime.fromtimestamp(float(value))
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
