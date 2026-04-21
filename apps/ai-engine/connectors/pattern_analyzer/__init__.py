"""
Aegis Pattern Analyzer — Layer 2B of the AI SRE stack.

Takes a time series of incidents/alerts/logs and extracts:
  * Time-based patterns (day-of-week clustering, hour-of-day skew)
  * Week-over-week anomalies, burst detection
  * Recurring message templates (MinHash + Jaccard shingle clustering)
  * Service-correlation graphs (which services fire together)

The output is a structured `AnalysisResult` consumed by Layer 3 (Claude
Control Tower) as enriched context for incident reasoning — and rendered as
a markdown summary via `build_analysis_report`.

This module is deliberately decoupled from Part A (SigNoz connector). Events
are accepted via the `IncidentLike` Protocol — anything duck-typed works.

Public API:
    PatternAnalyzer       — orchestrator class
    AnalysisResult        — top-level dataclass
    TimePattern           — day-of-week / hour-of-day distributions
    ServiceCorrelation    — one edge in the correlation graph
    MessageCluster        — one template group with examples
    IncidentLike          — Protocol describing expected event shape
    TimeAnomaly, Burst    — time-series anomalies
    ServiceCorrelationGraph — graph-of-correlations

Typical usage:

    from connectors.pattern_analyzer import PatternAnalyzer, build_analysis_report

    analyzer = PatternAnalyzer()
    result   = analyzer.analyze(events)          # events: iterable of IncidentLike
    report   = build_analysis_report(result)     # dict with "json" + "markdown"
    claude_context = report["markdown"]          # ~1500 tokens, prompt-ready
"""
from __future__ import annotations

from .analyzer import (
    AnalysisResult,
    IncidentLike,
    PatternAnalyzer,
)
from .correlation import (
    ServiceCorrelation,
    ServiceCorrelationGraph,
    service_correlation_graph,
)
from .message_clustering import MessageCluster, cluster_messages
from .report import build_analysis_report
from .time_patterns import (
    Burst,
    TimeAnomaly,
    TimePattern,
    burst_detector,
    day_of_week_distribution,
    hour_of_day_skew,
    week_over_week_anomaly,
)

__all__ = [
    "AnalysisResult",
    "Burst",
    "IncidentLike",
    "MessageCluster",
    "PatternAnalyzer",
    "ServiceCorrelation",
    "ServiceCorrelationGraph",
    "TimeAnomaly",
    "TimePattern",
    "build_analysis_report",
    "burst_detector",
    "cluster_messages",
    "day_of_week_distribution",
    "hour_of_day_skew",
    "service_correlation_graph",
    "week_over_week_anomaly",
]
