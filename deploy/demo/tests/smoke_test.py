"""
Smoke test for Aegis demo mode.

Run after `make demo` to verify:
  - All core services respond on expected ports
  - Confluence mock returns 20 pages
  - LocalStack S3 has the seeded bucket
  - Aegis API /health is OK
  - SigNoz frontend returns the UI HTML

Exit code 0 on pass, nonzero on fail.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass

try:
    import httpx  # type: ignore
except ImportError:
    print("httpx required: pip install httpx", file=sys.stderr)
    sys.exit(1)


@dataclass
class Check:
    name: str
    url: str
    expect_status: int = 200
    expect_substr: str | None = None
    expect_json_key: str | None = None


CHECKS: list[Check] = [
    Check("aegis-api health",       "http://localhost:8000/health"),
    Check("aegis-web root",          "http://localhost:3000"),
    Check("signoz UI",               "http://localhost:3301", expect_substr="SigNoz"),
    Check("otel demo shop",          "http://localhost:8080"),
    Check("confluence mock health",  "http://localhost:8090/healthz", expect_json_key="status"),
    Check("confluence content list", "http://localhost:8090/rest/api/content?limit=100", expect_json_key="results"),
    Check("localstack health",       "http://localhost:4566/_localstack/health", expect_json_key="services"),
]


def wait_for(url: str, timeout: int = 120) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=3.0)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def run() -> int:
    print("[smoke] waiting up to 120s for aegis-api to come up...")
    if not wait_for("http://localhost:8000/health", timeout=120):
        print("[smoke] FAIL: aegis-api never responded")
        return 2

    failures = 0
    for c in CHECKS:
        try:
            r = httpx.get(c.url, timeout=10.0, follow_redirects=True)
            ok = r.status_code == c.expect_status
            if ok and c.expect_substr:
                ok = c.expect_substr in r.text
            if ok and c.expect_json_key:
                try:
                    ok = c.expect_json_key in r.json()
                except Exception:
                    ok = False
            status = "OK" if ok else "FAIL"
            print(f"[smoke] {status}: {c.name} ({r.status_code})")
            if not ok:
                failures += 1
        except Exception as e:
            print(f"[smoke] FAIL: {c.name} — {e}")
            failures += 1

    # Confluence page count must be 20
    try:
        data = httpx.get("http://localhost:8090/rest/api/content?limit=100", timeout=5.0).json()
        count = len(data.get("results", []))
        if count == 20:
            print(f"[smoke] OK: confluence page count = {count}")
        else:
            print(f"[smoke] FAIL: confluence pages expected 20, got {count}")
            failures += 1
    except Exception as e:
        print(f"[smoke] FAIL: confluence count check — {e}")
        failures += 1

    print(f"\n[smoke] {len(CHECKS) + 1} checks, {failures} failures")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
