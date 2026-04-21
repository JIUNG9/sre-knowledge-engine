"""Pydantic v2 models for SigNoz connector responses.

The models normalize the shape-shifty SigNoz query-service API into
stable Python dataclasses. They are intentionally permissive on input
(``extra="ignore"``) but strict on the fields Aegis actually consumes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Logs
# --------------------------------------------------------------------------- #


class LogEntry(BaseModel):
    """A single log row returned by ``/api/v1/logs``."""

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    body: str
    severity: str | None = None
    service: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    resources: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


class MetricPoint(BaseModel):
    """A single ``(timestamp, value)`` pair from an instant query."""

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    value: float
    labels: dict[str, str] = Field(default_factory=dict)


class MetricSeries(BaseModel):
    """A ``query_range`` result: one or more labelled series."""

    model_config = ConfigDict(extra="ignore")

    promql: str
    start: datetime
    end: datetime
    step_seconds: int
    series: list["MetricSeriesRow"] = Field(default_factory=list)


class MetricSeriesRow(BaseModel):
    """One labelled time-series inside a :class:`MetricSeries`."""

    model_config = ConfigDict(extra="ignore")

    labels: dict[str, str] = Field(default_factory=dict)
    points: list[MetricPoint] = Field(default_factory=list)


MetricSeries.model_rebuild()


# --------------------------------------------------------------------------- #
# Traces
# --------------------------------------------------------------------------- #


class TraceSpan(BaseModel):
    """A single span inside a trace."""

    model_config = ConfigDict(extra="ignore")

    span_id: str
    parent_span_id: str | None = None
    name: str
    service: str
    start_time: datetime
    duration_ms: float
    status_code: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    """A trace and its constituent spans."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str
    root_service: str | None = None
    root_operation: str | None = None
    start_time: datetime
    duration_ms: float
    spans: list[TraceSpan] = Field(default_factory=list)


class TraceSummary(BaseModel):
    """A single row from the ``/api/v1/traces`` list endpoint."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str
    service: str
    operation: str
    start_time: datetime
    duration_ms: float
    status_code: str | None = None
    span_count: int = 0


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #


AlertState = Literal["firing", "resolved", "inactive", "pending", "unknown"]


class AlertRule(BaseModel):
    """A SigNoz alert rule definition."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    severity: str | None = None
    state: AlertState = "unknown"
    expression: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)


class AlertEvent(BaseModel):
    """A single firing/resolved event for an alert rule."""

    model_config = ConfigDict(extra="ignore")

    rule_id: str
    rule_name: str
    state: AlertState
    value: float | None = None
    fired_at: datetime
    resolved_at: datetime | None = None
    labels: dict[str, str] = Field(default_factory=dict)
