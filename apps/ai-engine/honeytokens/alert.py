"""Alerting for honey-token hits.

When the scanner detects a hit we want three things to happen:

1. An OTel span is emitted with error status so incident response sees
   it in whatever observability backend (SigNoz/Tempo/Jaeger) is wired
   up. If `opentelemetry` is not installed the call is a no-op.
2. A webhook POST so downstream automation (Slack, PagerDuty, custom
   SOC pipeline) can react. Delivery uses `httpx` if available,
   otherwise `urllib.request`.
3. A loud stderr warning. Honey token hits are always serious — false
   positives are essentially impossible because the marker format is
   unique to this system.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import TYPE_CHECKING, Iterable, Optional

from .config import get_config

if TYPE_CHECKING:
    from .scanner import HoneyTokenHit

log = logging.getLogger("aegis.honeytokens.alert")


_BANNER = "!" * 72


def _emit_otel(hits: Iterable["HoneyTokenHit"]) -> None:
    try:  # pragma: no cover - exercised only when OTel is installed
        from opentelemetry import trace
        from opentelemetry.trace.status import Status, StatusCode
    except Exception:
        return
    tracer = trace.get_tracer(get_config().otel_service_name)
    for hit in hits:
        with tracer.start_as_current_span("aegis.honeytoken.hit") as span:
            span.set_attribute("honeytoken.marker", hit.marker)
            span.set_attribute("honeytoken.category", hit.category)
            span.set_attribute("honeytoken.offset", hit.offset)
            span.set_attribute("honeytoken.token_id", hit.token_id)
            span.set_status(Status(StatusCode.ERROR, "honey token leaked"))


def _emit_webhook(hits: Iterable["HoneyTokenHit"], url: str) -> None:
    payload = {
        "event": "aegis.honeytoken.hit",
        "count": 0,
        "hits": [],
    }
    hits_list = list(hits)
    payload["count"] = len(hits_list)
    payload["hits"] = [
        {
            "marker": h.marker,
            "category": h.category,
            "token_id": h.token_id,
            "offset": h.offset,
        }
        for h in hits_list
    ]
    body = json.dumps(payload).encode("utf-8")
    try:  # pragma: no cover - network I/O
        import httpx

        httpx.post(url, content=body, headers={"Content-Type": "application/json"}, timeout=5.0)
        return
    except Exception:
        pass
    try:  # pragma: no cover
        import urllib.request

        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=5.0).read()
    except Exception as exc:
        log.error("webhook delivery failed: %s", exc)


def _emit_stderr(hits: Iterable["HoneyTokenHit"]) -> None:
    hits_list = list(hits)
    if not hits_list:
        return
    print(_BANNER, file=sys.stderr)
    print(
        f"[AEGIS] HONEY TOKEN LEAK DETECTED — {len(hits_list)} hit(s)",
        file=sys.stderr,
    )
    for h in hits_list:
        print(
            f"  marker={h.marker} category={h.category} offset={h.offset}",
            file=sys.stderr,
        )
    print(_BANNER, file=sys.stderr)


def fire(hits: Iterable["HoneyTokenHit"], *, webhook_url: Optional[str] = None) -> None:
    """Dispatch all configured alert channels for the given hits.

    Safe to call with an empty iterable (no-op). Never raises; every
    channel is independently fault-tolerant so a broken webhook does
    not suppress OTel spans or stderr output.
    """
    cfg = get_config()
    hits_list = list(hits)
    if not hits_list:
        return
    if not cfg.enabled:
        return
    # Materialise once so generators are not exhausted.
    try:
        _emit_stderr(hits_list)
    except Exception as exc:  # pragma: no cover - defensive
        log.error("stderr alert failed: %s", exc)
    try:
        _emit_otel(hits_list)
    except Exception as exc:  # pragma: no cover
        log.error("otel alert failed: %s", exc)
    url = webhook_url or cfg.webhook_url or os.getenv("AEGIS_HONEY_WEBHOOK")
    if url:
        try:
            _emit_webhook(hits_list, url)
        except Exception as exc:  # pragma: no cover
            log.error("webhook alert failed: %s", exc)
