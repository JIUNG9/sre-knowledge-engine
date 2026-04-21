"""Tests for time_patterns primitives and TimePattern composition."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from connectors.pattern_analyzer.time_patterns import (
    build_time_pattern,
    burst_detector,
    day_of_week_distribution,
    hour_of_day_skew,
    week_over_week_anomaly,
)
from connectors.pattern_analyzer.tests.fixtures import Event, monday_9am_events


def test_day_of_week_distribution_is_zero_filled():
    dist = day_of_week_distribution([])
    assert set(dist.keys()) == set(range(7))
    assert all(v == 0 for v in dist.values())


def test_hour_of_day_distribution_is_zero_filled():
    dist = hour_of_day_skew([])
    assert set(dist.keys()) == set(range(24))
    assert all(v == 0 for v in dist.values())


def test_80pct_monday_9am_is_detected():
    events = monday_9am_events(total=100, monday_ratio=0.80, seed=42)
    tp = build_time_pattern(events)

    assert tp.total_events == 100
    # Monday = weekday 0
    assert tp.dominant_weekday == 0, f"expected Monday dominant, got {tp.dominant_weekday}"
    # Peak hour should be 8 or 9 (we jittered +/-30 minutes around 09:00)
    assert tp.dominant_hour in (8, 9), f"expected 8 or 9, got {tp.dominant_hour}"
    # Monday share should be >= 75% (we planted 80%, sampling allows some slack)
    assert tp.weekday_share >= 0.75, f"monday share too low: {tp.weekday_share}"
    # Top hotspot must be (Mon, 8 or 9)
    assert tp.hotspots, "expected at least one hotspot"
    top_d, top_h, top_c = tp.hotspots[0]
    assert top_d == 0 and top_h in (8, 9)
    # The Monday-9am (+/-1 hour) bucket should capture the bulk — even though
    # +/-30min jitter splits counts across hours 8 and 9, the combined top-2
    # hotspots on Monday at 8/9 should be the majority.
    mon_peak = sum(c for d, h, c in tp.hotspots if d == 0 and h in (8, 9))
    assert mon_peak >= 50, f"Monday 8-9 hotspot bucket too small: {mon_peak}"


def test_week_over_week_anomaly_detects_spike():
    # 3 baseline weeks @ ~20 events, then a spike week @ 200 events.
    base = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)  # Monday
    events: list[Event] = []
    for week in range(3):
        for i in range(20):
            events.append(
                Event(
                    timestamp=base + timedelta(weeks=week, hours=i),
                    service="s",
                    severity="info",
                    message="m",
                    trace_id=None,
                )
            )
    for i in range(200):
        events.append(
            Event(
                timestamp=base + timedelta(weeks=3, hours=i % 24),
                service="s",
                severity="error",
                message="m",
                trace_id=None,
            )
        )
    anoms = week_over_week_anomaly(events, z_threshold=2.0)
    assert anoms, "should detect at least one anomaly"
    # The spike week should be there with direction=spike
    assert any(a.direction == "spike" and a.count >= 150 for a in anoms)


def test_burst_detector_finds_short_spike():
    base = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    events: list[Event] = []
    # 10 minutes of quiet (1 event per minute)
    for i in range(10):
        events.append(
            Event(
                timestamp=base + timedelta(minutes=i),
                service="s",
                severity="info",
                message="m",
                trace_id=None,
            )
        )
    # 1 minute of burst (50 events in that minute)
    burst_start = base + timedelta(minutes=10)
    for i in range(50):
        events.append(
            Event(
                timestamp=burst_start + timedelta(seconds=i),
                service="s",
                severity="error",
                message="m",
                trace_id=None,
            )
        )
    # 10 more minutes of quiet
    for i in range(10):
        events.append(
            Event(
                timestamp=base + timedelta(minutes=12 + i),
                service="s",
                severity="info",
                message="m",
                trace_id=None,
            )
        )
    bursts = burst_detector(events, window_seconds=60, z_threshold=2.0)
    assert bursts, "should detect the burst"
    assert any(b.count >= 40 for b in bursts)


def test_naive_datetime_coerced_to_utc():
    events = [
        Event(
            timestamp=datetime(2026, 3, 2, 9, 0, 0),  # naive — Monday
            service="s",
            severity="error",
            message="m",
            trace_id=None,
        )
    ]
    dist = day_of_week_distribution(events)
    assert dist[0] == 1


def test_burst_detector_rejects_zero_window():
    with pytest.raises(ValueError):
        burst_detector([], window_seconds=0)
