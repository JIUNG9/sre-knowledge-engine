"""Alert rule and alert event lookups against SigNoz.

Endpoints used:

* ``GET /api/v1/rules``                     — list rule definitions
* ``GET /api/v1/alerts``                    — list currently-known alerts
* ``GET /api/v1/rules/{rule_id}/history``   — historical firings for a rule
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal

from connectors.models import AlertEvent, AlertRule
from connectors.signoz_client import SigNozClient


logger = logging.getLogger("aegis.connectors.alerts")


_RULES_PATH = "/api/v1/rules"
_ALERTS_PATH = "/api/v1/alerts"


AlertStateFilter = Literal["firing", "resolved"]


class AlertFetcher:
    """Alert rule + event inspection."""

    def __init__(self, client: SigNozClient) -> None:
        self._client = client

    async def list_rules(self) -> list[AlertRule]:
        """Return all alert rule definitions."""
        payload = await self._client.get(_RULES_PATH)
        rules = _parse_rules(payload)
        logger.info("alert_fetcher.list_rules returned=%d", len(rules))
        return rules

    async def list_alerts(
        self,
        state: AlertStateFilter | None = None,
    ) -> list[AlertEvent]:
        """Return currently-tracked alert events.

        Args:
            state: Optional filter. ``"firing"`` or ``"resolved"`` — any
                other value is rejected at the type level.
        """
        params: dict[str, Any] = {}
        if state:
            params["state"] = state

        payload = await self._client.get(_ALERTS_PATH, params=params or None)
        events = _parse_events(payload)

        if state:
            events = [e for e in events if e.state == state]

        logger.info(
            "alert_fetcher.list_alerts state=%s returned=%d",
            state,
            len(events),
        )
        return events

    async def get_alert_history(
        self,
        rule_id: str,
        start: datetime,
        end: datetime,
    ) -> list[AlertEvent]:
        """Return firings/resolutions for a single rule within a range."""
        if not rule_id:
            raise ValueError("rule_id must be non-empty")
        if end <= start:
            raise ValueError("end must be after start")

        params = {
            "start": int(start.timestamp() * 1000),
            "end": int(end.timestamp() * 1000),
        }
        payload = await self._client.get(
            f"{_RULES_PATH}/{rule_id}/history",
            params=params,
        )
        events = _parse_events(payload, fallback_rule_id=rule_id)

        logger.info(
            "alert_fetcher.get_alert_history rule_id=%s start=%s end=%s returned=%d",
            rule_id,
            start.isoformat(),
            end.isoformat(),
            len(events),
        )
        return events


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _parse_rules(payload: Any) -> list[AlertRule]:
    rows = _extract_rows(payload, keys=("rules", "data", "items"))
    rules: list[AlertRule] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rule_id = str(row.get("id") or row.get("ruleId") or row.get("rule_id") or "")
        if not rule_id:
            continue
        rules.append(
            AlertRule(
                id=rule_id,
                name=str(row.get("alert") or row.get("name") or row.get("ruleName") or rule_id),
                severity=row.get("severity") or (row.get("labels") or {}).get("severity"),
                state=_normalize_state(row.get("state")),
                expression=row.get("expr") or row.get("expression"),
                labels=row.get("labels") or {},
                annotations=row.get("annotations") or {},
            )
        )
    return rules


def _parse_events(payload: Any, fallback_rule_id: str = "") -> list[AlertEvent]:
    rows = _extract_rows(payload, keys=("alerts", "items", "data", "history"))
    events: list[AlertEvent] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        fired_at = _parse_ts(
            row.get("firedAt")
            or row.get("fired_at")
            or row.get("activeAt")
            or row.get("startsAt")
        )
        if fired_at is None:
            continue
        rule_id = str(
            row.get("ruleId")
            or row.get("rule_id")
            or row.get("id")
            or fallback_rule_id
        )
        events.append(
            AlertEvent(
                rule_id=rule_id,
                rule_name=str(row.get("ruleName") or row.get("alertname") or row.get("name") or rule_id),
                state=_normalize_state(row.get("state")),
                value=_coerce_float(row.get("value")),
                fired_at=fired_at,
                resolved_at=_parse_ts(row.get("resolvedAt") or row.get("resolved_at") or row.get("endsAt")),
                labels=row.get("labels") or {},
            )
        )
    return events


def _extract_rows(payload: Any, *, keys: tuple[str, ...]) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    data = payload.get("data", payload)
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value

    # Some SigNoz versions wrap once more: {"data": {"data": [...]}}.
    for key in keys:
        nested = data.get(key)
        if isinstance(nested, dict):
            for inner_key in keys:
                inner = nested.get(inner_key)
                if isinstance(inner, list):
                    return inner
    return []


def _normalize_state(raw: Any) -> Any:
    """Coerce SigNoz/Prometheus state strings to the Literal alphabet."""
    if not raw:
        return "unknown"
    s = str(raw).lower()
    if s in {"firing", "resolved", "inactive", "pending"}:
        return s
    # Prometheus uses "active" for firing-ish rules.
    if s == "active":
        return "firing"
    return "unknown"


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
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
