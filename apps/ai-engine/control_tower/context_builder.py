"""Build a :class:`Context` object for a given alert + mode.

The context builder is the glue between Layer 3 and the data-producing
layers (1 wiki, 2 connectors, 2B pattern analyzer). It never calls the
LLM; it only pulls and normalizes inputs so the orchestrator can hand
a prompt-ready block to the router.

All fetchers are accepted via dependency injection. Passing ``None``
for any fetcher disables that data source — useful for eco mode and
for tests where you want to exercise one branch of the pipeline
without mocking everything else.

Token-budget enforcement is soft. We trim the worst offenders (logs,
metrics) first, then wiki snippets. If after trimming we are still
over budget we record a warning on the context rather than blowing up.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from .config import InvestigationModeName
from .investigation import (
    Alert,
    Context,
    LogSummary,
    MetricSummary,
    PatternFinding,
    TraceHint,
    WikiSnippet,
)
from .modes import ModeSpec, get_mode_spec

logger = logging.getLogger("aegis.control_tower.context")


# --------------------------------------------------------------------------- #
# Protocols — fetchers are duck-typed so tests can inject simple stubs.
# --------------------------------------------------------------------------- #


class WikiQueryable(Protocol):
    """Duck-type for :class:`wiki.WikiEngine`.

    Only the ``query(topic)`` method is required. Production WikiEngine
    does not ship ``query`` yet (its public surface is ``ingest`` +
    ``load_vault``) — the control tower calls ``query`` via a small
    adapter (see :class:`WikiAdapter`) that walks the cached pages
    with a naive substring search.
    """

    def query(self, topic: str, *, limit: int = 5) -> list[WikiSnippet]: ...


class LogFetcherLike(Protocol):
    async def search(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[Any]: ...


class MetricFetcherLike(Protocol):
    async def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step_seconds: int,
    ) -> Any: ...


class TraceFetcherLike(Protocol):
    async def search(
        self,
        service: str | None,
        operation: str | None,
        min_duration_ms: int | None,
        start: datetime,
        end: datetime,
    ) -> list[Any]: ...


class AlertFetcherLike(Protocol):
    async def get_alert_history(
        self, rule_id: str, start: datetime, end: datetime
    ) -> list[Any]: ...


class PatternAnalyzerLike(Protocol):
    def analyze(self, events: Any) -> Any: ...


# --------------------------------------------------------------------------- #
# Default queries
# --------------------------------------------------------------------------- #


def _topic_for_alert(alert: Alert) -> str:
    """Derive a wiki lookup topic from an alert."""
    if alert.service:
        return alert.service
    if alert.title:
        return alert.title
    if alert.question:
        return alert.question
    return "overview"


def _log_query_for_alert(alert: Alert) -> str:
    """Build a conservative log DSL query for the alert's service."""
    parts: list[str] = []
    if alert.service:
        parts.append(f"service={alert.service}")
    if alert.severity in ("warning", "critical"):
        parts.append("level=error")
    return " AND ".join(parts) if parts else "level=error"


def _promql_for_alert(alert: Alert) -> str:
    """Default PromQL probe — request rate by service for 5 minutes."""
    service = alert.service or "unknown"
    return (
        f'sum(rate(http_requests_total{{service="{service}"}}[5m])) '
        f'by (service)'
    )


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #


class ContextBuilder:
    """Assemble a :class:`Context` for an alert + mode.

    Every fetcher is optional. Missing fetchers are treated as "this
    data source is unavailable in this deployment" — the builder logs a
    debug line and continues. Exceptions from a fetcher are caught and
    converted to warnings on the context so one flaky connector can't
    break the whole investigation.
    """

    def __init__(
        self,
        *,
        wiki: WikiQueryable | None = None,
        log_fetcher: LogFetcherLike | None = None,
        metric_fetcher: MetricFetcherLike | None = None,
        trace_fetcher: TraceFetcherLike | None = None,
        alert_fetcher: AlertFetcherLike | None = None,
        pattern_analyzer: PatternAnalyzerLike | None = None,
        lookback_minutes: int = 15,
        log_limit: int = 10,
        trace_limit: int = 5,
    ) -> None:
        self.wiki = wiki
        self.log_fetcher = log_fetcher
        self.metric_fetcher = metric_fetcher
        self.trace_fetcher = trace_fetcher
        self.alert_fetcher = alert_fetcher
        self.pattern_analyzer = pattern_analyzer
        self.lookback_minutes = lookback_minutes
        self.log_limit = log_limit
        self.trace_limit = trace_limit

    # ------------------------------------------------------------------ #
    # Public entry points
    # ------------------------------------------------------------------ #

    async def build(
        self,
        alert: Alert,
        mode: InvestigationModeName,
        *,
        budget_tokens: int,
    ) -> Context:
        """Assemble a :class:`Context` for ``alert`` in ``mode``.

        The method always returns a Context — it never raises for a
        down connector. Notes and warnings are captured inside the
        returned object so the orchestrator can surface them.
        """
        spec: ModeSpec = get_mode_spec(mode)
        ctx = Context(mode=mode, budget_tokens=budget_tokens)
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=self.lookback_minutes)

        if spec.include_wiki:
            ctx.wiki_pages = self._pull_wiki(alert)

        if spec.include_metrics:
            metrics = await self._pull_metrics(alert, start, now)
            ctx.metrics = metrics

        if spec.include_logs:
            logs = await self._pull_logs(alert, start, now)
            ctx.logs = logs

        if spec.include_traces:
            traces = await self._pull_traces(alert, start, now)
            ctx.traces = traces

        if spec.include_alert_history:
            history = await self._pull_alert_history(alert, start, now)
            ctx.alert_history = history

        if spec.run_pattern_analyzer and self.pattern_analyzer is not None:
            finding = self._run_pattern_analyzer(ctx, alert)
            if finding is not None:
                ctx.patterns = finding

        self._enforce_budget(ctx)
        return ctx

    # ------------------------------------------------------------------ #
    # Individual pulls
    # ------------------------------------------------------------------ #

    def _pull_wiki(self, alert: Alert) -> list[WikiSnippet]:
        if self.wiki is None:
            return []
        topic = _topic_for_alert(alert)
        try:
            snippets = list(self.wiki.query(topic, limit=5))
        except Exception as exc:  # noqa: BLE001
            logger.debug("wiki query failed for topic=%s: %s", topic, exc)
            return []
        return [s for s in snippets if isinstance(s, WikiSnippet)]

    async def _pull_metrics(
        self, alert: Alert, start: datetime, end: datetime
    ) -> list[MetricSummary]:
        if self.metric_fetcher is None:
            return []
        promql = _promql_for_alert(alert)
        try:
            series = await self.metric_fetcher.query_range(
                promql, start=start, end=end, step_seconds=60
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("metric query failed promql=%s: %s", promql, exc)
            return []

        rows = getattr(series, "series", []) or []
        summaries: list[MetricSummary] = []
        for row in rows:
            points = getattr(row, "points", []) or []
            last_value = points[-1].value if points else None
            summaries.append(
                MetricSummary(
                    promql=promql,
                    series_count=len(rows),
                    last_value=last_value,
                    labels=dict(getattr(row, "labels", {}) or {}),
                )
            )
        if not summaries:
            summaries.append(
                MetricSummary(
                    promql=promql, series_count=0, last_value=None
                )
            )
        return summaries

    async def _pull_logs(
        self, alert: Alert, start: datetime, end: datetime
    ) -> list[LogSummary]:
        if self.log_fetcher is None:
            return []
        query = _log_query_for_alert(alert)
        try:
            entries = await self.log_fetcher.search(
                query, start=start, end=end, limit=self.log_limit
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("log query failed q=%s: %s", query, exc)
            return []

        summaries: list[LogSummary] = []
        for entry in entries:
            summaries.append(
                LogSummary(
                    timestamp=getattr(entry, "timestamp", start),
                    severity=getattr(entry, "severity", None),
                    service=getattr(entry, "service", None),
                    body=(getattr(entry, "body", "") or "")[:400],
                )
            )
        return summaries

    async def _pull_traces(
        self, alert: Alert, start: datetime, end: datetime
    ) -> list[TraceHint]:
        if self.trace_fetcher is None:
            return []
        try:
            summaries = await self.trace_fetcher.search(
                service=alert.service,
                operation=None,
                min_duration_ms=None,
                start=start,
                end=end,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "trace query failed service=%s: %s", alert.service, exc
            )
            return []

        out: list[TraceHint] = []
        for s in list(summaries)[: self.trace_limit]:
            out.append(
                TraceHint(
                    trace_id=str(getattr(s, "trace_id", "")),
                    service=str(getattr(s, "service", "")),
                    operation=str(getattr(s, "operation", "")),
                    duration_ms=float(getattr(s, "duration_ms", 0.0)),
                    status_code=getattr(s, "status_code", None),
                )
            )
        return out

    async def _pull_alert_history(
        self, alert: Alert, start: datetime, end: datetime
    ) -> list[str]:
        if self.alert_fetcher is None:
            return []
        rule_id = alert.labels.get("rule_id") or alert.labels.get("alertname")
        if not rule_id:
            return []
        try:
            events = await self.alert_fetcher.get_alert_history(
                rule_id, start, end
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "alert history failed rule=%s: %s", rule_id, exc
            )
            return []

        lines: list[str] = []
        for event in list(events)[:5]:
            fired = getattr(event, "fired_at", None)
            fired_iso = (
                fired.isoformat(timespec="seconds") if fired else "unknown"
            )
            state = getattr(event, "state", "unknown")
            lines.append(f"{fired_iso} state={state}")
        return lines

    def _run_pattern_analyzer(
        self, ctx: Context, alert: Alert
    ) -> PatternFinding | None:
        if self.pattern_analyzer is None:
            return None
        # Build duck-typed event objects from logs so pattern analyzer can
        # consume them. If no logs are present the analyzer has nothing
        # to say — skip silently.
        events = [
            _LogIncident(
                timestamp=line.timestamp,
                service=line.service,
                severity=line.severity or "info",
                message=line.body,
                trace_id=None,
            )
            for line in ctx.logs
        ]
        if not events:
            return None
        try:
            result = self.pattern_analyzer.analyze(events)
        except Exception as exc:  # noqa: BLE001
            logger.debug("pattern analyzer failed: %s", exc)
            return None

        markdown = ""
        try:
            from connectors.pattern_analyzer import build_analysis_report

            report = build_analysis_report(result)
            markdown = str(report.get("markdown", ""))
        except Exception as exc:  # noqa: BLE001
            logger.debug("build_analysis_report failed: %s", exc)

        return PatternFinding(
            total_events=int(getattr(result, "total_events", 0)),
            markdown=markdown,
            bursts=len(getattr(result, "bursts", []) or []),
            correlations=len(
                getattr(getattr(result, "correlation_graph", None), "edges", [])
                or []
            ),
        )

    # ------------------------------------------------------------------ #
    # Budget enforcement
    # ------------------------------------------------------------------ #

    def _enforce_budget(self, ctx: Context) -> None:
        """Trim context elements to stay under the token budget.

        We use a crude heuristic (4 characters ~= 1 token) and trim the
        largest contributors first. This is deliberately approximate —
        true token counts come from the downstream tokenizer; the
        budget here is a safety net, not a promise.
        """
        budget_chars = max(512, ctx.budget_tokens * 4)
        rendered = ctx.render()
        if len(rendered) <= budget_chars:
            return

        overflow = len(rendered) - budget_chars
        ctx.notes.append(
            f"context trimmed: exceeded budget by ~{overflow} chars"
        )

        # Trim in order: logs > traces > alert_history > metrics > wiki
        if overflow > 0 and ctx.logs:
            ctx.logs = ctx.logs[: max(1, len(ctx.logs) // 2)]
            overflow = max(0, overflow - 600)
        if overflow > 0 and ctx.traces:
            ctx.traces = ctx.traces[: max(1, len(ctx.traces) // 2)]
            overflow = max(0, overflow - 400)
        if overflow > 0 and ctx.alert_history:
            ctx.alert_history = ctx.alert_history[:2]
            overflow = max(0, overflow - 200)
        if overflow > 0 and ctx.metrics:
            ctx.metrics = ctx.metrics[: max(1, len(ctx.metrics) // 2)]
            overflow = max(0, overflow - 200)
        if overflow > 0 and ctx.wiki_pages:
            ctx.wiki_pages = ctx.wiki_pages[: max(1, len(ctx.wiki_pages) // 2)]


# --------------------------------------------------------------------------- #
# Internal
# --------------------------------------------------------------------------- #


class _LogIncident:
    """Duck-typed event for :class:`PatternAnalyzer`."""

    __slots__ = ("timestamp", "service", "severity", "message", "trace_id")

    def __init__(
        self,
        timestamp: datetime,
        service: str | None,
        severity: str,
        message: str,
        trace_id: str | None,
    ) -> None:
        self.timestamp = timestamp
        self.service = service
        self.severity = severity
        self.message = message
        self.trace_id = trace_id


# --------------------------------------------------------------------------- #
# WikiEngine adapter
# --------------------------------------------------------------------------- #


class WikiAdapter:
    """Adapter that exposes :meth:`query` on top of a :class:`WikiEngine`.

    WikiEngine itself ships with ``ingest`` + ``load_vault`` but no
    retrieval method. This adapter provides a simple substring/keyword
    search over the in-memory vault so the control tower can keep
    calling ``wiki.query(topic)``. If WikiEngine later grows a native
    query, the adapter becomes a thin passthrough.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def query(self, topic: str, *, limit: int = 5) -> list[WikiSnippet]:
        pages = getattr(self._engine, "_pages", None) or []
        topic_low = topic.lower().strip()
        ranked: list[tuple[int, Any]] = []
        for page in pages:
            title = getattr(page, "title", "") or ""
            slug = getattr(page, "slug", "") or ""
            body = getattr(page, "body", "") or ""
            score = 0
            if topic_low and topic_low in title.lower():
                score += 3
            if topic_low and topic_low in slug.lower():
                score += 2
            if topic_low and topic_low in body.lower():
                score += 1
            if score:
                ranked.append((score, page))
        ranked.sort(key=lambda row: row[0], reverse=True)
        out: list[WikiSnippet] = []
        for _, page in ranked[:limit]:
            body = (getattr(page, "body", "") or "").strip()
            snippet = body[:300] + ("..." if len(body) > 300 else "")
            out.append(
                WikiSnippet(
                    slug=getattr(page, "slug", ""),
                    title=getattr(page, "title", ""),
                    type=str(getattr(page, "type", "concept")),
                    snippet=snippet,
                    last_updated=getattr(page, "last_updated", None),
                )
            )
        return out
