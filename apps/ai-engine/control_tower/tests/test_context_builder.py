"""ContextBuilder tests with mocked fetchers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from control_tower.context_builder import ContextBuilder, WikiAdapter
from control_tower.investigation import Alert, WikiSnippet


# --------------------------------------------------------------------------- #
# Stubs
# --------------------------------------------------------------------------- #


class StubWiki:
    def __init__(self, pages: list[WikiSnippet]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, int]] = []

    def query(self, topic: str, *, limit: int = 5) -> list[WikiSnippet]:
        self.calls.append((topic, limit))
        return self.pages[:limit]


class StubLogFetcher:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.calls = 0

    async def search(self, query, start, end, limit=500):
        self.calls += 1
        return self.rows


class StubMetricFetcher:
    def __init__(self, series_rows: list[object]) -> None:
        self._rows = series_rows

    async def query_range(self, promql, start, end, step_seconds):
        return SimpleNamespace(
            promql=promql,
            start=start,
            end=end,
            step_seconds=step_seconds,
            series=self._rows,
        )


class StubTraceFetcher:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    async def search(self, service, operation, min_duration_ms, start, end):
        return self.rows


class StubAlertFetcher:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    async def get_alert_history(self, rule_id, start, end):
        return self.rows


class StubPatternAnalyzer:
    def __init__(self) -> None:
        self.called = False

    def analyze(self, events):
        self.called = True
        return SimpleNamespace(
            total_events=len(list(events)),
            time_pattern=SimpleNamespace(
                total_events=len(list(events)),
                weekday_share=0.2,
                hour_share=0.1,
                dominant_weekday=1,
                dominant_hour=9,
                hotspots=[],
            ),
            week_anomalies=[],
            bursts=[SimpleNamespace()] * 2,
            message_clusters=[],
            correlation_graph=SimpleNamespace(
                edges=[SimpleNamespace(), SimpleNamespace(), SimpleNamespace()],
                services=[],
                window_seconds=60,
                top_pairs=lambda n: [],
            ),
            severity_counts={},
            trace_coverage=0.0,
        )


def _log_row(**kwargs):
    base = {
        "timestamp": datetime.now(timezone.utc),
        "body": "error opening connection",
        "severity": "error",
        "service": "acme-api",
        "trace_id": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _metric_row(value=0.42):
    return SimpleNamespace(
        labels={"service": "acme-api"},
        points=[SimpleNamespace(value=value, timestamp=datetime.now(timezone.utc))],
    )


def _trace_row():
    return SimpleNamespace(
        trace_id="t-1",
        service="acme-api",
        operation="GET /health",
        duration_ms=120.0,
        status_code="OK",
    )


def _alert_event(rule_id="r-1"):
    return SimpleNamespace(
        rule_id=rule_id,
        state="firing",
        fired_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_build_eco_pulls_only_wiki():
    wiki = StubWiki([
        WikiSnippet(slug="acme-api", title="Acme API", snippet="primary API"),
    ])
    logs = StubLogFetcher([_log_row()])
    metrics = StubMetricFetcher([_metric_row()])

    builder = ContextBuilder(
        wiki=wiki, log_fetcher=logs, metric_fetcher=metrics
    )
    ctx = await builder.build(
        Alert(service="acme-api", severity="critical"),
        mode="eco",
        budget_tokens=2000,
    )

    assert ctx.mode == "eco"
    assert len(ctx.wiki_pages) == 1
    assert ctx.logs == []
    assert ctx.metrics == []
    assert ctx.traces == []
    assert logs.calls == 0
    assert wiki.calls  # wiki queried


@pytest.mark.asyncio
async def test_build_standard_includes_telemetry():
    wiki = StubWiki([
        WikiSnippet(slug="acme-api", title="Acme API", snippet="primary")
    ])
    logs = StubLogFetcher([_log_row(), _log_row()])
    metrics = StubMetricFetcher([_metric_row(0.55)])
    alerts = StubAlertFetcher([_alert_event()])

    builder = ContextBuilder(
        wiki=wiki,
        log_fetcher=logs,
        metric_fetcher=metrics,
        alert_fetcher=alerts,
    )
    ctx = await builder.build(
        Alert(
            service="acme-api",
            severity="critical",
            labels={"rule_id": "r-1"},
        ),
        mode="standard",
        budget_tokens=6000,
    )

    assert ctx.mode == "standard"
    assert len(ctx.logs) == 2
    assert len(ctx.metrics) >= 1
    assert len(ctx.alert_history) == 1
    # Standard mode does NOT include traces.
    assert ctx.traces == []


@pytest.mark.asyncio
async def test_build_deep_runs_pattern_analyzer():
    wiki = StubWiki([
        WikiSnippet(slug="acme-api", title="Acme API", snippet="primary")
    ])
    logs = StubLogFetcher([_log_row() for _ in range(5)])
    metrics = StubMetricFetcher([_metric_row()])
    traces = StubTraceFetcher([_trace_row()])
    pa = StubPatternAnalyzer()

    builder = ContextBuilder(
        wiki=wiki,
        log_fetcher=logs,
        metric_fetcher=metrics,
        trace_fetcher=traces,
        pattern_analyzer=pa,
    )
    ctx = await builder.build(
        Alert(service="acme-api", severity="critical"),
        mode="deep",
        budget_tokens=12000,
    )

    assert ctx.mode == "deep"
    assert len(ctx.traces) == 1
    assert pa.called is True
    assert ctx.patterns is not None
    assert ctx.patterns.total_events == 5


@pytest.mark.asyncio
async def test_build_handles_missing_fetchers():
    builder = ContextBuilder()
    ctx = await builder.build(
        Alert(service="acme-api"), mode="standard", budget_tokens=4000
    )
    assert ctx.wiki_pages == []
    assert ctx.logs == []
    assert ctx.metrics == []


@pytest.mark.asyncio
async def test_build_tolerates_fetcher_exceptions():
    class BoomLogs:
        async def search(self, *a, **k):
            raise RuntimeError("signoz down")

    class BoomMetrics:
        async def query_range(self, *a, **k):
            raise RuntimeError("prom down")

    builder = ContextBuilder(
        log_fetcher=BoomLogs(), metric_fetcher=BoomMetrics()
    )
    ctx = await builder.build(
        Alert(service="acme-api"), mode="standard", budget_tokens=4000
    )
    # The builder swallowed the errors and kept going.
    assert ctx.logs == []
    assert ctx.metrics == []


@pytest.mark.asyncio
async def test_budget_enforcement_trims_logs():
    wiki = StubWiki([
        WikiSnippet(slug=f"p-{i}", title=f"Page {i}", snippet="x" * 200)
        for i in range(5)
    ])
    logs = StubLogFetcher(
        [_log_row(body="x" * 300) for _ in range(20)]
    )
    metrics = StubMetricFetcher([_metric_row()])

    builder = ContextBuilder(
        wiki=wiki,
        log_fetcher=logs,
        metric_fetcher=metrics,
        log_limit=20,
    )
    ctx = await builder.build(
        Alert(service="acme-api"),
        mode="standard",
        budget_tokens=512,
    )
    # Budget enforcement should have trimmed logs and emitted a note.
    assert any("context trimmed" in n for n in ctx.notes)
    assert len(ctx.logs) < 20


@pytest.mark.asyncio
async def test_alert_history_skipped_without_rule_id():
    alerts = StubAlertFetcher([_alert_event()])
    builder = ContextBuilder(alert_fetcher=alerts)
    ctx = await builder.build(
        Alert(service="acme-api"), mode="standard", budget_tokens=4000
    )
    assert ctx.alert_history == []


def test_wiki_adapter_substring_ranking():
    page1 = SimpleNamespace(
        title="Acme API runbook",
        slug="acme-api-runbook",
        body="the Acme API exposes /health",
        last_updated=datetime.now(timezone.utc),
        type="runbook",
    )
    page2 = SimpleNamespace(
        title="Overview",
        slug="overview",
        body="unrelated overview page",
        last_updated=datetime.now(timezone.utc),
        type="concept",
    )
    engine = SimpleNamespace(_pages=[page1, page2])
    adapter = WikiAdapter(engine)

    results = adapter.query("acme")
    assert results
    assert results[0].slug == "acme-api-runbook"
    assert isinstance(results[0], WikiSnippet)


def test_wiki_adapter_no_pages():
    adapter = WikiAdapter(SimpleNamespace(_pages=[]))
    assert adapter.query("anything") == []


@pytest.mark.asyncio
async def test_pattern_analyzer_skipped_with_no_logs():
    pa = StubPatternAnalyzer()
    builder = ContextBuilder(pattern_analyzer=pa)
    ctx = await builder.build(
        Alert(service="acme-api"), mode="deep", budget_tokens=12000
    )
    # No logs, nothing to feed the pattern analyzer.
    assert pa.called is False
    assert ctx.patterns is None
