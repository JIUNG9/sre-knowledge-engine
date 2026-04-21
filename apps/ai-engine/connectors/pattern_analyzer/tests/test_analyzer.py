"""End-to-end PatternAnalyzer test: 200 synthetic events, report shape."""
from __future__ import annotations

import json

from connectors.pattern_analyzer import (
    AnalysisResult,
    PatternAnalyzer,
    build_analysis_report,
)
from connectors.pattern_analyzer.tests.fixtures import (
    mixed_realistic_stream,
    monday_9am_events,
)


def test_analyze_end_to_end_shape():
    events = mixed_realistic_stream(total=200, seed=99)
    analyzer = PatternAnalyzer()
    result = analyzer.analyze(events)

    assert isinstance(result, AnalysisResult)
    assert result.total_events == len(events)
    # Time pattern present
    assert result.time_pattern.total_events == len(events)
    assert 0.0 <= result.time_pattern.weekday_share <= 1.0
    # Severity counts cover >90% of events (info/warn/error/critical)
    assert sum(result.severity_counts.values()) >= int(len(events) * 0.9)
    # Trace coverage between 0 and 1
    assert 0.0 <= result.trace_coverage <= 1.0
    # Message clusters <= configured cap
    assert len(result.message_clusters) <= 20
    # Correlation graph has expected pair (service-a, service-b)
    svcs = set(result.correlation_graph.services)
    assert {"service-a", "service-b"} <= svcs

    report = build_analysis_report(result)
    assert set(report.keys()) == {"json", "markdown"}
    # JSON is round-trippable
    json.dumps(report["json"])
    assert isinstance(report["markdown"], str)
    # Markdown headline references events and a weekday
    assert "Pattern Analysis" in report["markdown"]
    assert str(len(events)) in report["markdown"]


def test_analyze_is_deterministic():
    events = mixed_realistic_stream(total=200, seed=99)
    a = PatternAnalyzer().analyze(events)
    b = PatternAnalyzer().analyze(events)
    assert a.total_events == b.total_events
    assert a.time_pattern == b.time_pattern
    assert [c.template for c in a.message_clusters] == [c.template for c in b.message_clusters]
    assert [(e.source, e.target) for e in a.correlation_graph.edges] == [
        (e.source, e.target) for e in b.correlation_graph.edges
    ]


def test_monday_9am_report_headline_mentions_monday():
    events = monday_9am_events(total=100, monday_ratio=0.80, seed=42)
    result = PatternAnalyzer().analyze(events)
    report = build_analysis_report(result)
    md = report["markdown"]
    assert "Mon" in md, "report should call out Monday"
    assert result.time_pattern.weekday_share >= 0.75


def test_empty_input():
    result = PatternAnalyzer().analyze([])
    assert result.total_events == 0
    assert result.time_pattern.dominant_weekday is None
    report = build_analysis_report(result)
    assert "0 events" in report["markdown"]
