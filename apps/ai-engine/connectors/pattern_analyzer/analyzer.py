"""
PatternAnalyzer — orchestrates time, message, and correlation primitives.

The public shape is deliberately small: construct a `PatternAnalyzer`, call
`.analyze(events)`, get an `AnalysisResult`. Everything downstream
(`build_analysis_report`, Layer 3 Claude prompt assembly) consumes the
result dataclass — not the raw events.

Input is typed as `IncidentLike` — a Protocol describing the attributes we
read. This intentionally DOES NOT import Part A's connector types, so
pattern_analyzer can be tested and published independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Iterator, Protocol, runtime_checkable

from .correlation import ServiceCorrelationGraph, service_correlation_graph
from .message_clustering import MessageCluster, cluster_messages
from .time_patterns import (
    Burst,
    TimeAnomaly,
    TimePattern,
    build_time_pattern,
    burst_detector,
    week_over_week_anomaly,
)


@runtime_checkable
class IncidentLike(Protocol):
    """Duck-typed shape of an incident / alert / log event.

    Any object with these attributes works — dataclasses, pydantic models,
    plain namedtuples, even `types.SimpleNamespace`. Part A's SigNoz
    connector produces objects that satisfy this Protocol by construction.
    """

    timestamp: datetime
    service: str | None
    severity: str
    message: str
    trace_id: str | None


@dataclass(frozen=True)
class AnalysisResult:
    """Top-level structured output of `PatternAnalyzer.analyze()`."""

    total_events: int
    time_pattern: TimePattern
    week_anomalies: list[TimeAnomaly]
    bursts: list[Burst]
    message_clusters: list[MessageCluster]
    correlation_graph: ServiceCorrelationGraph
    severity_counts: dict[str, int] = field(default_factory=dict)
    trace_coverage: float = 0.0  # fraction of events with a trace_id


class PatternAnalyzer:
    """Stateless orchestrator — reusable across calls, thread-safe.

    All knobs are constructor-configured; `analyze()` is deterministic given
    the same events and parameters.

    Parameters
    ----------
    burst_window_seconds : size of burst-detector buckets (default 60)
    burst_z_threshold    : z-score above which a bucket counts as a burst
    wow_z_threshold      : z-score for week-over-week anomalies
    corr_window_seconds  : rolling window for service correlation
    corr_min_score       : minimum edge score to retain
    max_clusters         : message-clustering cap
    """

    def __init__(
        self,
        *,
        burst_window_seconds: int = 60,
        burst_z_threshold: float = 3.0,
        wow_z_threshold: float = 2.0,
        corr_window_seconds: int = 300,
        corr_min_score: float = 0.3,
        max_clusters: int = 20,
    ) -> None:
        self.burst_window_seconds = burst_window_seconds
        self.burst_z_threshold = burst_z_threshold
        self.wow_z_threshold = wow_z_threshold
        self.corr_window_seconds = corr_window_seconds
        self.corr_min_score = corr_min_score
        self.max_clusters = max_clusters

    # --------------------------------------------------------------
    # Core entry point
    # --------------------------------------------------------------

    def analyze(self, events: Iterable[IncidentLike]) -> AnalysisResult:
        """Run the full pattern-analysis pipeline.

        Events are materialised ONCE into a list so the multiple primitives
        can iterate — if you pass a generator we consume it. For truly huge
        streams, chunk upstream and merge the resulting AnalysisResults at
        the caller (future work — not needed for 1M events, which fits
        comfortably in memory as a list of dataclasses).
        """
        buf: list[IncidentLike] = list(events)
        total = len(buf)

        severity_counts: dict[str, int] = {}
        trace_hits = 0
        for ev in buf:
            sev = getattr(ev, "severity", None)
            if isinstance(sev, str):
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            if getattr(ev, "trace_id", None):
                trace_hits += 1
        trace_coverage = (trace_hits / total) if total else 0.0

        time_pattern = build_time_pattern(buf)
        wow = week_over_week_anomaly(buf, z_threshold=self.wow_z_threshold)
        bursts = burst_detector(
            buf,
            window_seconds=self.burst_window_seconds,
            z_threshold=self.burst_z_threshold,
        )
        clusters = cluster_messages(buf, max_clusters=self.max_clusters)
        corr = service_correlation_graph(
            buf,
            window_seconds=self.corr_window_seconds,
            min_score=self.corr_min_score,
        )

        return AnalysisResult(
            total_events=total,
            time_pattern=time_pattern,
            week_anomalies=wow,
            bursts=bursts,
            message_clusters=clusters,
            correlation_graph=corr,
            severity_counts=severity_counts,
            trace_coverage=trace_coverage,
        )

    # --------------------------------------------------------------
    # Streaming helper — exposed for callers who want to chunk
    # --------------------------------------------------------------

    def chunks(
        self, events: Iterable[IncidentLike], size: int = 50_000
    ) -> Iterator[list[IncidentLike]]:
        """Yield fixed-size chunks from an iterable — handy for map/reduce."""
        buf: list[IncidentLike] = []
        for ev in events:
            buf.append(ev)
            if len(buf) >= size:
                yield buf
                buf = []
        if buf:
            yield buf
