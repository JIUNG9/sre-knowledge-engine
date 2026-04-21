"""
Seed 24h of synthetic incidents into the Aegis API.

Implements the realistic "Monday 9am spike" pattern so Article #6
(pattern-detection) has reproducible data to demo against.

Usage:
    python seed_incidents.py [--api http://localhost:8000] [--count 48]
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover
    httpx = None  # allow dry-run without deps

SERVICES = [
    "checkout", "cart", "payment-gateway", "recommendation",
    "product-catalog", "ad", "shipping", "email", "frontend",
]
SEVERITIES = ["SEV1", "SEV2", "SEV3", "SEV4"]
TITLE_TEMPLATES = [
    "High error rate on {svc}",
    "p95 latency breach — {svc}",
    "Memory pressure — {svc}",
    "5xx spike from {svc}",
    "Deployment regression — {svc}",
    "Database connection exhaustion — {svc}",
]


def monday_9am_weight(ts: datetime) -> float:
    """Return multiplier so Mondays 9-10 UTC get 80% concentration."""
    if ts.weekday() == 0 and ts.hour == 9:
        return 8.0
    if ts.weekday() == 0:
        return 1.5
    return 1.0


def generate_incidents(count: int = 48) -> list[dict]:
    now = datetime.now(timezone.utc)
    incidents: list[dict] = []
    rng = random.Random(42)  # deterministic

    for i in range(count):
        offset = rng.randint(0, 24 * 60)
        ts = now - timedelta(minutes=offset)
        weight = monday_9am_weight(ts)
        if rng.random() > (1.0 / weight):
            # skew incidents toward the weighted window
            ts = now.replace(hour=9, minute=rng.randint(0, 59)) - timedelta(days=rng.randint(0, 3) * 7)
        svc = rng.choice(SERVICES)
        incidents.append({
            "id": f"INC-DEMO-{1000 + i}",
            "title": rng.choice(TITLE_TEMPLATES).format(svc=svc),
            "service": svc,
            "severity": rng.choices(SEVERITIES, weights=[1, 3, 6, 4])[0],
            "status": rng.choice(["open", "acknowledged", "resolved", "resolved", "resolved"]),
            "created_at": ts.isoformat(),
            "source": "demo-seed",
        })
    return incidents


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--count", type=int, default=48)
    ap.add_argument("--output", default="/tmp/aegis-demo-incidents.json")
    args = ap.parse_args()

    incidents = generate_incidents(args.count)
    Path(args.output).write_text(json.dumps(incidents, indent=2))
    print(f"[seed_incidents] wrote {len(incidents)} incidents to {args.output}")

    if httpx is None:
        print("[seed_incidents] httpx not installed — skipping API push")
        return

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{args.api}/demo/incidents/bulk", json={"incidents": incidents})
            print(f"[seed_incidents] POST {resp.url} -> {resp.status_code}")
    except Exception as e:  # pragma: no cover
        print(f"[seed_incidents] API push failed ({e}) — file saved anyway")


if __name__ == "__main__":
    main()
