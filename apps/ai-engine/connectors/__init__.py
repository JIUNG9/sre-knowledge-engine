"""Aegis telemetry connectors — Layer 2.

Public API for the SigNoz connector: an async HTTP client plus four
fetcher modules for logs, metrics (PromQL), traces, and alerts.

Example:
    from connectors import (
        SigNozClient,
        SigNozConnectorConfig,
        LogFetcher,
        MetricFetcher,
        TraceFetcher,
        AlertFetcher,
    )

    cfg = SigNozConnectorConfig(base_url="http://signoz:3301", api_key="...")
    async with SigNozClient.from_config(cfg) as client:
        logs = await LogFetcher(client).search("level=error", start, end)

Every fetcher returns Pydantic v2 models from :mod:`connectors.models`.
Network calls honor the existing Aegis telemetry/proxy stack; this
module never speaks directly to the Anthropic API.
"""

from __future__ import annotations

from connectors.alert_fetcher import AlertFetcher
from connectors.config import SigNozConnectorConfig
from connectors.log_fetcher import LogFetcher
from connectors.metric_fetcher import MetricFetcher
from connectors.models import (
    AlertEvent,
    AlertRule,
    LogEntry,
    MetricPoint,
    MetricSeries,
    Trace,
    TraceSpan,
    TraceSummary,
)
from connectors.signoz_client import SigNozClient, SigNozError
from connectors.trace_fetcher import TraceFetcher

__all__ = [
    "AlertEvent",
    "AlertFetcher",
    "AlertRule",
    "LogEntry",
    "LogFetcher",
    "MetricFetcher",
    "MetricPoint",
    "MetricSeries",
    "SigNozClient",
    "SigNozConnectorConfig",
    "SigNozError",
    "Trace",
    "TraceFetcher",
    "TraceSpan",
    "TraceSummary",
]
