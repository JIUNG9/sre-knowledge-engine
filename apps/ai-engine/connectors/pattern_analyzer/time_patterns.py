"""
Time-based pattern detection for incidents/alerts/logs.

All functions are pure: input is an iterable of events (anything with a
tz-aware `timestamp: datetime`), output is a plain data structure.

Naive datetimes are assumed UTC and coerced — this is stated in the
contract and tested; we don't silently guess.

Four primitives:
    day_of_week_distribution(events)   -> {weekday_int: count}   (0=Monday)
    hour_of_day_skew(events)           -> {hour: count}          (0-23, UTC)
    week_over_week_anomaly(events)     -> [TimeAnomaly]
    burst_detector(events, window_seconds, z_threshold) -> [Burst]

These are composed by `PatternAnalyzer.analyze()` but also usable standalone.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol, runtime_checkable


@runtime_checkable
class _HasTimestamp(Protocol):
    timestamp: datetime


# ---------------------------------------------------------------------------
# Dataclasses returned by time-pattern primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimePattern:
    """Combined day-of-week and hour-of-day distribution with hotspots.

    `dominant_weekday` and `dominant_hour` are the argmax of their respective
    distributions — or None when the input is empty.

    `weekday_share` is the share (0..1) of events falling on the dominant
    weekday, which is the headline number for Article #6 ("80% of incidents
    on Monday 9am").
    """

    total_events: int
    day_of_week: dict[int, int]
    hour_of_day: dict[int, int]
    dominant_weekday: int | None
    dominant_hour: int | None
    weekday_share: float
    hour_share: float
    hotspots: list[tuple[int, int, int]] = field(default_factory=list)
    # hotspots: list of (weekday, hour, count) sorted desc, top N


@dataclass(frozen=True)
class TimeAnomaly:
    """One week-over-week anomaly bucket.

    `week_start` is the Monday (UTC, midnight) of the anomalous week.
    `z_score` uses baseline mean/stdev of prior weeks; values >= 2.0 are
    worth flagging. Inf/NaN are clamped to a finite sentinel.
    """

    week_start: datetime
    count: int
    baseline_mean: float
    baseline_stdev: float
    z_score: float
    direction: str  # "spike" | "drop"


@dataclass(frozen=True)
class Burst:
    """A single detected burst window.

    Rolling `window_seconds` buckets whose count z-score exceeds the given
    threshold (default 3.0). Overlapping adjacent bursts are merged.
    """

    start: datetime
    end: datetime
    count: int
    z_score: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_utc(dt: datetime) -> datetime:
    """Coerce naive datetime to UTC; convert aware datetimes to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iter_timestamps(events: Iterable[_HasTimestamp]) -> Iterable[datetime]:
    """Yield tz-aware UTC timestamps; skip events without one."""
    for ev in events:
        ts = getattr(ev, "timestamp", None)
        if isinstance(ts, datetime):
            yield _as_utc(ts)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def day_of_week_distribution(events: Iterable[_HasTimestamp]) -> dict[int, int]:
    """Count events by ISO weekday (0=Monday, 6=Sunday).

    Always returns all 7 keys (zero-filled) to keep downstream code simple.
    Memory-bounded: O(1) — only a 7-slot Counter.
    """
    counter: Counter[int] = Counter()
    for ts in _iter_timestamps(events):
        counter[ts.weekday()] += 1
    return {d: counter.get(d, 0) for d in range(7)}


def hour_of_day_skew(events: Iterable[_HasTimestamp]) -> dict[int, int]:
    """Count events by hour-of-day (0-23 UTC). All 24 keys present."""
    counter: Counter[int] = Counter()
    for ts in _iter_timestamps(events):
        counter[ts.hour] += 1
    return {h: counter.get(h, 0) for h in range(24)}


def week_over_week_anomaly(
    events: Iterable[_HasTimestamp],
    z_threshold: float = 2.0,
) -> list[TimeAnomaly]:
    """Detect weeks whose count deviates significantly from the historical
    baseline (all prior weeks).

    Implementation: bucket by ISO-week-start (Monday 00:00 UTC). For each
    week, compute z-score vs. the running mean/stdev of earlier weeks. Emit
    any week whose |z| >= threshold once we have at least 2 weeks of
    history (stdev is undefined with fewer).
    """
    buckets: dict[datetime, int] = defaultdict(int)
    for ts in _iter_timestamps(events):
        # Monday of that week at 00:00 UTC
        monday = ts - timedelta(days=ts.weekday())
        week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets[week_start] += 1

    if not buckets:
        return []

    weeks_sorted = sorted(buckets.items())
    anomalies: list[TimeAnomaly] = []
    history: list[int] = []
    for week_start, count in weeks_sorted:
        if len(history) >= 2:
            mean = statistics.fmean(history)
            stdev = statistics.pstdev(history)
            if stdev > 0:
                z = (count - mean) / stdev
                flag = abs(z) >= z_threshold
            else:
                # Zero-variance baseline: any deviation at all is an anomaly.
                # Report a finite but clearly large z so downstream code doesn't
                # special-case infinities.
                if count == mean:
                    z = 0.0
                    flag = False
                else:
                    z = math.copysign(99.0, count - mean)
                    flag = True
            if flag:
                anomalies.append(
                    TimeAnomaly(
                        week_start=week_start,
                        count=count,
                        baseline_mean=mean,
                        baseline_stdev=stdev,
                        z_score=z,
                        direction="spike" if z > 0 else "drop",
                    )
                )
        history.append(count)
    return anomalies


def burst_detector(
    events: Iterable[_HasTimestamp],
    window_seconds: int = 60,
    z_threshold: float = 3.0,
) -> list[Burst]:
    """Detect short bursts using fixed-size time buckets + z-score.

    Approach: bucket events into `window_seconds`-wide tumbling windows
    (anchored at the first event), compute mean/stdev across all windows,
    emit windows whose z-score >= threshold. Adjacent qualifying windows
    are merged into a single Burst.

    Memory: O(W) where W = (span / window_seconds). For 1M events over a
    year at 60s windows that's ~525k ints — a few MB.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be > 0")

    timestamps = sorted(_iter_timestamps(events))
    if not timestamps:
        return []

    anchor = timestamps[0]
    buckets: dict[int, int] = defaultdict(int)
    for ts in timestamps:
        idx = int((ts - anchor).total_seconds()) // window_seconds
        buckets[idx] += 1

    counts = list(buckets.values())
    if len(counts) < 2:
        return []
    mean = statistics.fmean(counts)
    stdev = statistics.pstdev(counts)
    if stdev == 0:
        return []

    # Collect qualifying bucket indices in order
    qualifying: list[tuple[int, int, float]] = []  # (idx, count, z)
    for idx in sorted(buckets.keys()):
        c = buckets[idx]
        z = (c - mean) / stdev
        if z >= z_threshold:
            qualifying.append((idx, c, z))

    if not qualifying:
        return []

    # Merge adjacent buckets
    bursts: list[Burst] = []
    cur_start_idx = qualifying[0][0]
    cur_end_idx = qualifying[0][0]
    cur_count = qualifying[0][1]
    cur_z = qualifying[0][2]
    for idx, c, z in qualifying[1:]:
        if idx == cur_end_idx + 1:
            cur_end_idx = idx
            cur_count += c
            cur_z = max(cur_z, z)
        else:
            bursts.append(
                Burst(
                    start=anchor + timedelta(seconds=cur_start_idx * window_seconds),
                    end=anchor
                    + timedelta(seconds=(cur_end_idx + 1) * window_seconds),
                    count=cur_count,
                    z_score=cur_z,
                )
            )
            cur_start_idx = idx
            cur_end_idx = idx
            cur_count = c
            cur_z = z
    bursts.append(
        Burst(
            start=anchor + timedelta(seconds=cur_start_idx * window_seconds),
            end=anchor + timedelta(seconds=(cur_end_idx + 1) * window_seconds),
            count=cur_count,
            z_score=cur_z,
        )
    )
    return bursts


def build_time_pattern(
    events: Iterable[_HasTimestamp],
    top_hotspots: int = 5,
) -> TimePattern:
    """Build a composite TimePattern in a single pass."""
    dow: Counter[int] = Counter()
    hod: Counter[int] = Counter()
    grid: Counter[tuple[int, int]] = Counter()
    total = 0
    for ts in _iter_timestamps(events):
        total += 1
        dow[ts.weekday()] += 1
        hod[ts.hour] += 1
        grid[(ts.weekday(), ts.hour)] += 1

    day_dict = {d: dow.get(d, 0) for d in range(7)}
    hour_dict = {h: hod.get(h, 0) for h in range(24)}

    dom_weekday = max(day_dict, key=day_dict.get) if total else None
    dom_hour = max(hour_dict, key=hour_dict.get) if total else None
    weekday_share = (day_dict[dom_weekday] / total) if (total and dom_weekday is not None) else 0.0
    hour_share = (hour_dict[dom_hour] / total) if (total and dom_hour is not None) else 0.0

    hotspots = [(d, h, c) for (d, h), c in grid.most_common(top_hotspots)]

    return TimePattern(
        total_events=total,
        day_of_week=day_dict,
        hour_of_day=hour_dict,
        dominant_weekday=dom_weekday,
        dominant_hour=dom_hour,
        weekday_share=weekday_share,
        hour_share=hour_share,
        hotspots=hotspots,
    )
