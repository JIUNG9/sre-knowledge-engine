"""Log search against SigNoz ``/api/v1/logs``.

SigNoz's logs API evolves faster than its docs — this module wraps the
currently-shipping shape and normalises rows into :class:`LogEntry`.
Pagination is opaque: SigNoz returns an optional ``next_page`` token
which we forward unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from connectors.models import LogEntry
from connectors.signoz_client import SigNozClient


logger = logging.getLogger("aegis.connectors.logs")


_LOGS_PATH = "/api/v1/logs"


class LogFetcher:
    """Search logs by free-form query string + time range."""

    def __init__(self, client: SigNozClient) -> None:
        self._client = client

    async def search(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[LogEntry]:
        """Return up to ``limit`` log rows matching ``query``.

        Args:
            query: SigNoz log-search DSL (e.g. ``"service=gateway AND level=error"``).
            start: Inclusive lower bound (UTC assumed if naive).
            end: Exclusive upper bound.
            limit: Max rows across all pages. Pagination stops as soon
                as this many rows are collected.

        Pagination is automatic: the fetcher follows ``next_page``
        tokens until ``limit`` is reached or the server stops sending
        a token.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        if end <= start:
            raise ValueError("end must be after start")

        collected: list[LogEntry] = []
        next_page: str | None = None

        while len(collected) < limit:
            remaining = limit - len(collected)
            params: dict[str, Any] = {
                "q": query,
                "start": _to_nanos(start),
                "end": _to_nanos(end),
                "limit": remaining,
            }
            if next_page:
                params["page"] = next_page

            payload = await self._client.get(_LOGS_PATH, params=params)
            rows, next_page = _parse_logs_payload(payload)
            if not rows:
                break

            for row in rows:
                entry = _row_to_log_entry(row)
                if entry is not None:
                    collected.append(entry)
                    if len(collected) >= limit:
                        break

            if not next_page:
                break

        logger.info(
            "log_fetcher.search query=%r start=%s end=%s returned=%d",
            query,
            start.isoformat(),
            end.isoformat(),
            len(collected),
        )
        return collected


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _to_nanos(dt: datetime) -> int:
    """SigNoz expects Unix time in **nanoseconds** for log time ranges."""
    return int(dt.timestamp() * 1_000_000_000)


def _parse_logs_payload(payload: Any) -> tuple[list[dict], str | None]:
    """Tolerate the two shapes SigNoz uses.

    Shape A (recent)::

        {"data": {"logs": [...], "next_page": "..."}}

    Shape B (older)::

        {"result": [{"list": [...]}]}
    """
    if not isinstance(payload, dict):
        return [], None

    data = payload.get("data")
    if isinstance(data, dict) and "logs" in data:
        rows = data.get("logs") or []
        next_page = data.get("next_page") or data.get("nextPage")
        return list(rows), next_page if isinstance(next_page, str) else None

    result = payload.get("result")
    if isinstance(result, list) and result:
        first = result[0] if isinstance(result[0], dict) else {}
        rows = first.get("list") or []
        return list(rows), None

    return [], None


def _row_to_log_entry(row: dict) -> LogEntry | None:
    """Best-effort map a raw log row to :class:`LogEntry`."""
    if not isinstance(row, dict):
        return None

    ts_raw = (
        row.get("timestamp")
        or row.get("ts")
        or row.get("time")
    )
    ts = _coerce_timestamp(ts_raw)
    if ts is None:
        return None

    body = (
        row.get("body")
        or row.get("message")
        or row.get("msg")
        or ""
    )
    attributes = row.get("attributes") or row.get("attributes_string") or {}
    resources = row.get("resources") or row.get("resources_string") or {}

    return LogEntry(
        timestamp=ts,
        body=str(body),
        severity=row.get("severity_text") or row.get("severity") or row.get("level"),
        service=(
            row.get("service")
            or (resources.get("service.name") if isinstance(resources, dict) else None)
        ),
        trace_id=row.get("trace_id") or row.get("traceId"),
        span_id=row.get("span_id") or row.get("spanId"),
        attributes=attributes if isinstance(attributes, dict) else {},
        resources=resources if isinstance(resources, dict) else {},
    )


def _coerce_timestamp(value: Any) -> datetime | None:
    """SigNoz emits timestamps as ns integers, ms integers, or RFC3339."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # Nanoseconds since epoch are > 10**17 for any plausible date;
        # microseconds ~ 10**15; milliseconds ~ 10**12; seconds ~ 10**9.
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
