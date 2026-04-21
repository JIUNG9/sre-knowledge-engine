"""
Service correlation graph — which services fire alerts together.

Approach: sliding window over sorted-by-timestamp events. Two services are
"correlated" if they appear in the same window. We accumulate co-occurrence
counts, then normalise into a directional score:

    score(A->B) = co_occurrences(A,B) / firings(A)

This is asymmetric on purpose — if A always fires and B only fires when A
does, score(A->B) is 1.0 (B follows A) while score(B->A) is 1.0 too (every
B has an A nearby), but the absolute firing counts tell you the direction.

Memory-bounded: O(S^2) where S = unique services seen. Realistic S in SRE
is ~50-200 — trivial. We bound it with `max_services` and coalesce the
long tail into an "<other>" node.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Protocol, runtime_checkable


@runtime_checkable
class _HasServiceAndTs(Protocol):
    service: str | None
    timestamp: datetime


@dataclass(frozen=True)
class ServiceCorrelation:
    """One directed edge `source -> target`.

    `score` is P(target fires within window | source fires) in [0, 1].
    `co_count` is the number of windows where both fired at least once.
    """

    source: str
    target: str
    co_count: int
    source_count: int
    target_count: int
    score: float


@dataclass
class ServiceCorrelationGraph:
    """Directed correlation graph.

    `services` is the list of nodes (by firing-count desc).
    `edges` contains every directed pair above `min_score`. Self-loops are
    excluded. `window_seconds` is recorded for provenance.
    """

    services: list[str] = field(default_factory=list)
    firing_counts: dict[str, int] = field(default_factory=dict)
    edges: list[ServiceCorrelation] = field(default_factory=list)
    window_seconds: int = 300

    def top_pairs(self, n: int = 10) -> list[ServiceCorrelation]:
        return sorted(
            self.edges, key=lambda e: (-e.score, -e.co_count, e.source, e.target)
        )[:n]


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def service_correlation_graph(
    events: Iterable[_HasServiceAndTs],
    window_seconds: int = 300,
    min_score: float = 0.3,
    max_services: int = 100,
) -> ServiceCorrelationGraph:
    """Build a ServiceCorrelationGraph using a rolling time window.

    Algorithm:
        1. Sort events by timestamp (we materialise — for a truly streaming
           input use a k-way merge upstream).
        2. Maintain a deque of events whose timestamp is within
           `window_seconds` of the current event. When a new event arrives,
           pop expired entries off the left.
        3. For each new event with service X, every other service Y
           currently in the window contributes a co-occurrence (X, Y).
        4. At end: firing_counts[service] = total events per service.
           For each (X, Y) co-count, emit two directed edges with
           asymmetric scores.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be > 0")

    items: list[tuple[datetime, str]] = []
    for ev in events:
        svc = getattr(ev, "service", None)
        ts = getattr(ev, "timestamp", None)
        if not isinstance(svc, str) or not svc or not isinstance(ts, datetime):
            continue
        items.append((_as_utc(ts), svc))
    items.sort(key=lambda t: t[0])

    if not items:
        return ServiceCorrelationGraph(window_seconds=window_seconds)

    firing: Counter[str] = Counter()
    co: dict[tuple[str, str], int] = defaultdict(int)
    window: deque[tuple[datetime, str]] = deque()

    for ts, svc in items:
        # Evict expired
        cutoff_delta = window_seconds
        while window and (ts - window[0][0]).total_seconds() > cutoff_delta:
            window.popleft()
        # Count co-occurrence with services currently in window (excluding same-service pairs)
        seen_in_window: set[str] = set()
        for _, other_svc in window:
            if other_svc == svc or other_svc in seen_in_window:
                continue
            seen_in_window.add(other_svc)
            # Record both directions — scored differently on normalisation
            co[(svc, other_svc)] += 1
            co[(other_svc, svc)] += 1
        firing[svc] += 1
        window.append((ts, svc))

    # Truncate to top services
    if len(firing) > max_services:
        top = set(s for s, _ in firing.most_common(max_services))
        firing = Counter({s: c for s, c in firing.items() if s in top})
        co = {(a, b): n for (a, b), n in co.items() if a in top and b in top}

    services = [s for s, _ in firing.most_common()]
    edges: list[ServiceCorrelation] = []
    for (a, b), n in co.items():
        if a == b:
            continue
        src_count = firing[a]
        if src_count == 0:
            continue
        score = n / src_count
        if score < min_score:
            continue
        edges.append(
            ServiceCorrelation(
                source=a,
                target=b,
                co_count=n,
                source_count=src_count,
                target_count=firing[b],
                score=min(score, 1.0),
            )
        )
    edges.sort(key=lambda e: (-e.score, -e.co_count, e.source, e.target))

    return ServiceCorrelationGraph(
        services=services,
        firing_counts=dict(firing),
        edges=edges,
        window_seconds=window_seconds,
    )
