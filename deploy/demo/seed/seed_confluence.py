"""
Seed / verify the Confluence mock has 20 pages with staleness variety.

The confluence-mock container already loads pages.json on startup.
This script simply validates the fixtures are reachable and reports
stale vs current page counts for the demo dashboard.

Usage:
    python seed_confluence.py [--url http://localhost:8090]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

try:
    import httpx  # type: ignore
except ImportError:
    print("[seed_confluence] httpx required: pip install httpx", file=sys.stderr)
    sys.exit(1)

STALE_CUTOFF_DAYS = 365


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8090")
    args = ap.parse_args()

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{args.url}/rest/api/content", params={"limit": 100})
        resp.raise_for_status()
        data = resp.json()

    pages = data.get("results", [])
    now = datetime.now(timezone.utc)
    stale = 0
    current = 0
    for p in pages:
        when = p.get("version", {}).get("when")
        if not when:
            continue
        ts = datetime.fromisoformat(when.replace("Z", "+00:00"))
        age_days = (now - ts).days
        if age_days > STALE_CUTOFF_DAYS:
            stale += 1
        else:
            current += 1

    print(f"[seed_confluence] total={len(pages)} stale={stale} current={current}")
    if len(pages) != 20:
        print(f"[seed_confluence] WARNING: expected 20 pages, got {len(pages)}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
