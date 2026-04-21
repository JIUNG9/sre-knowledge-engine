"""
Synthetic event fixtures for pattern_analyzer tests.

Everything here is deterministic (seeded) so tests are repeatable.
`Event` is a minimal namedtuple-like dataclass that satisfies the
`IncidentLike` Protocol.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class Event:
    """Minimal event dataclass that duck-types `IncidentLike`."""

    timestamp: datetime
    service: Optional[str]
    severity: str
    message: str
    trace_id: Optional[str]


def monday_9am_events(
    total: int = 100,
    monday_ratio: float = 0.8,
    seed: int = 42,
) -> list[Event]:
    """Generate `total` events where `monday_ratio` fall on Monday around 9am UTC.

    The rest are scattered uniformly across a 4-week window.
    """
    rng = random.Random(seed)
    base_monday = datetime(2026, 3, 2, 9, 0, 0, tzinfo=timezone.utc)  # Monday
    events: list[Event] = []
    n_monday = int(round(total * monday_ratio))

    for i in range(n_monday):
        # Random week 0..3 at Monday 9am +/- 30 min
        week = rng.randint(0, 3)
        minute_jitter = rng.randint(-30, 30)
        ts = base_monday + timedelta(weeks=week, minutes=minute_jitter)
        events.append(
            Event(
                timestamp=ts,
                service=rng.choice(["api-gateway", "auth-svc", "db-primary"]),
                severity=rng.choice(["warn", "error", "critical"]),
                message="Database connection pool exhausted on host-"
                + str(rng.randint(1, 9)),
                trace_id=f"{rng.randrange(16**16):016x}",
            )
        )

    # Scatter the rest across 4 weeks, any weekday, any hour, but NOT Monday 9am
    span_seconds = 4 * 7 * 24 * 3600
    while len(events) < total:
        offset = rng.randint(0, span_seconds)
        ts = base_monday.replace(hour=0) + timedelta(seconds=offset)
        if ts.weekday() == 0 and 8 <= ts.hour <= 9:
            # avoid polluting the Monday-9am signal
            continue
        events.append(
            Event(
                timestamp=ts,
                service=rng.choice(["api-gateway", "auth-svc", "db-primary"]),
                severity=rng.choice(["info", "warn", "error"]),
                message=rng.choice(
                    [
                        "User login succeeded for u-" + str(rng.randint(1, 999)),
                        "Cache miss for key item:" + str(rng.randint(1, 99999)),
                        "HTTP 200 OK in " + str(rng.randint(10, 900)) + "ms",
                    ]
                ),
                trace_id=None if rng.random() < 0.2 else f"{rng.randrange(16**16):016x}",
            )
        )
    rng.shuffle(events)
    return events


def templated_log_lines(
    per_template: int = 10,
    seed: int = 7,
) -> list[Event]:
    """Generate `per_template * 5` events drawn from 5 underlying templates."""
    rng = random.Random(seed)
    templates: list[tuple[str, str]] = [
        # (severity, template-with-{var})
        ("error", "Connection refused to upstream {host}:{port} after {ms}ms"),
        ("warn", "Slow query took {ms}ms on shard {shard}"),
        ("info", "User {user_id} logged in from {ip}"),
        ("error", "Failed to acquire lock for resource-{res} (owner={owner})"),
        ("critical", "OOM killed process pid={pid} rss={mb}MB"),
    ]
    events: list[Event] = []
    base = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    for t_idx, (sev, tmpl) in enumerate(templates):
        for i in range(per_template):
            msg = tmpl.format(
                host=f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                port=rng.randint(1024, 65535),
                ms=rng.randint(10, 9999),
                shard=rng.randint(0, 15),
                user_id=rng.randint(1, 99999),
                ip=f"192.168.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                res=rng.randint(1, 500),
                owner=f"{rng.randrange(16**16):016x}",
                pid=rng.randint(1000, 99999),
                mb=rng.randint(100, 8000),
            )
            events.append(
                Event(
                    timestamp=base + timedelta(minutes=t_idx * per_template + i),
                    service="svc-" + str(t_idx),
                    severity=sev,
                    message=msg,
                    trace_id=f"{rng.randrange(16**16):016x}",
                )
            )
    return events


def correlated_services(
    n_pairs: int = 30,
    seed: int = 11,
) -> list[Event]:
    """Generate `n_pairs` (A,B) joint firings plus some independent C firings.

    A and B always fire within 60s of each other. C fires alone, offset by
    hours, producing near-zero correlation with either.
    """
    rng = random.Random(seed)
    base = datetime(2026, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
    events: list[Event] = []
    # Paired A and B — B fires 5-30s after A
    for i in range(n_pairs):
        t_a = base + timedelta(hours=i * 2)  # every 2 hours
        t_b = t_a + timedelta(seconds=rng.randint(5, 30))
        events.append(
            Event(
                timestamp=t_a,
                service="service-a",
                severity="error",
                message="A fired " + str(i),
                trace_id=None,
            )
        )
        events.append(
            Event(
                timestamp=t_b,
                service="service-b",
                severity="error",
                message="B followed " + str(i),
                trace_id=None,
            )
        )
    # Independent C — scatter far from any A/B
    for i in range(n_pairs):
        t_c = base + timedelta(hours=i * 2 + 1)  # midway between A-pairs
        events.append(
            Event(
                timestamp=t_c,
                service="service-c",
                severity="warn",
                message="C independent " + str(i),
                trace_id=None,
            )
        )
    rng.shuffle(events)
    return events


def mixed_realistic_stream(
    total: int = 200,
    seed: int = 99,
) -> list[Event]:
    """Mixed realistic fake stream — used for end-to-end analyzer tests."""
    events = monday_9am_events(total=total // 2, seed=seed)
    events.extend(templated_log_lines(per_template=total // 20, seed=seed + 1))
    events.extend(correlated_services(n_pairs=total // 10, seed=seed + 2))
    return events
