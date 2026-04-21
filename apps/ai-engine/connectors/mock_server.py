"""In-process mock SigNoz server.

Wired via :class:`httpx.MockTransport` so nothing ever hits the
network — ideal for unit tests, CI pipelines without a SigNoz stack,
and the ``use_mock=True`` dev flag on :class:`SigNozConnectorConfig`.

The canned data is deliberately small but covers the shape each
fetcher needs. For richer scenarios, build a custom transport in your
test and pass it to :meth:`SigNozClient` directly.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable

import httpx


MockHandler = Callable[[httpx.Request], httpx.Response]


def build_mock_transport() -> httpx.MockTransport:
    """Return a :class:`httpx.MockTransport` that answers every path."""
    return httpx.MockTransport(_dispatch)


def _dispatch(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/v1/logs":
        return _json(_canned_logs())
    if path == "/api/v1/query_range":
        return _json(_canned_metrics(request))
    if path == "/api/v1/traces":
        return _json(_canned_trace_list())
    if path.startswith("/api/v1/traces/"):
        trace_id = path.rsplit("/", 1)[-1]
        return _json(_canned_trace_detail(trace_id))
    if path == "/api/v1/rules":
        return _json(_canned_rules())
    if path == "/api/v1/alerts":
        return _json(_canned_alerts())
    if path.startswith("/api/v1/rules/") and path.endswith("/history"):
        rule_id = path.split("/")[-2]
        return _json(_canned_rule_history(rule_id))
    return httpx.Response(404, json={"error": f"mock has no route for {path}"})


def _json(body: Any) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(body).encode(), headers={"content-type": "application/json"})


# --------------------------------------------------------------------------- #
# Canned payloads
# --------------------------------------------------------------------------- #


def _canned_logs() -> dict:
    now_ns = int(time.time() * 1_000_000_000)
    return {
        "data": {
            "logs": [
                {
                    "timestamp": now_ns - 2_000_000_000,
                    "body": "GET /health 200",
                    "severity_text": "INFO",
                    "service": "gateway",
                    "trace_id": "abc123",
                    "span_id": "s1",
                    "attributes": {"http.status_code": 200},
                    "resources": {"service.name": "gateway"},
                },
                {
                    "timestamp": now_ns - 1_000_000_000,
                    "body": "OOM killed: user-svc",
                    "severity_text": "ERROR",
                    "service": "user-svc",
                    "trace_id": "abc123",
                    "span_id": "s2",
                    "attributes": {"container.memory.usage": 2048},
                    "resources": {"service.name": "user-svc"},
                },
            ],
            "next_page": None,
        }
    }


def _canned_metrics(request: httpx.Request) -> dict:
    start = int(request.url.params.get("start") or time.time() - 60)
    end = int(request.url.params.get("end") or time.time())
    step = max(int(request.url.params.get("step") or 30), 1)
    values = []
    t = start
    v = 0.5
    while t <= end:
        values.append([t, f"{v:.4f}"])
        t += step
        v += 0.1
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"service": "gateway", "method": "GET"},
                    "values": values or [[start, "0"]],
                }
            ],
        },
    }


def _canned_trace_list() -> dict:
    now_ns = int(time.time() * 1_000_000_000)
    return {
        "data": {
            "traces": [
                {
                    "traceId": "abc123",
                    "serviceName": "gateway",
                    "operation": "GET /health",
                    "startTime": now_ns - 5_000_000_000,
                    "durationMs": 42.1,
                    "statusCode": "OK",
                    "spanCount": 3,
                }
            ]
        }
    }


def _canned_trace_detail(trace_id: str) -> dict:
    now_ns = int(time.time() * 1_000_000_000)
    return {
        "data": {
            "traceId": trace_id,
            "rootService": "gateway",
            "rootOperation": "GET /health",
            "startTime": now_ns - 5_000_000_000,
            "durationMs": 42.1,
            "spans": [
                {
                    "spanId": "s1",
                    "parentSpanId": None,
                    "name": "GET /health",
                    "serviceName": "gateway",
                    "startTime": now_ns - 5_000_000_000,
                    "durationMs": 42.1,
                    "statusCode": "OK",
                    "attributes": {"http.status_code": 200},
                },
                {
                    "spanId": "s2",
                    "parentSpanId": "s1",
                    "name": "db.query",
                    "serviceName": "postgres",
                    "startTime": now_ns - 4_800_000_000,
                    "durationMs": 12.3,
                    "statusCode": "OK",
                    "attributes": {"db.statement": "SELECT 1"},
                },
            ],
        }
    }


def _canned_rules() -> dict:
    return {
        "data": {
            "rules": [
                {
                    "id": "rule-1",
                    "name": "High error rate — gateway",
                    "severity": "critical",
                    "state": "firing",
                    "expr": 'rate(http_requests_total{status="5xx"}[5m]) > 0.05',
                    "labels": {"team": "sre"},
                    "annotations": {"runbook": "https://wiki.aegis/5xx"},
                },
                {
                    "id": "rule-2",
                    "name": "Pod memory saturation",
                    "severity": "warning",
                    "state": "inactive",
                    "expr": "container_memory_usage_bytes > 0.9 * container_memory_limit_bytes",
                    "labels": {"team": "platform"},
                    "annotations": {},
                },
            ]
        }
    }


def _canned_alerts() -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "data": {
            "alerts": [
                {
                    "ruleId": "rule-1",
                    "ruleName": "High error rate — gateway",
                    "state": "firing",
                    "value": 0.12,
                    "firedAt": now_ms - 300_000,
                    "labels": {"team": "sre"},
                },
                {
                    "ruleId": "rule-2",
                    "ruleName": "Pod memory saturation",
                    "state": "resolved",
                    "value": 0.7,
                    "firedAt": now_ms - 7_200_000,
                    "resolvedAt": now_ms - 3_600_000,
                    "labels": {"team": "platform"},
                },
            ]
        }
    }


def _canned_rule_history(rule_id: str) -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "data": {
            "history": [
                {
                    "ruleId": rule_id,
                    "ruleName": "High error rate — gateway",
                    "state": "firing",
                    "value": 0.12,
                    "firedAt": now_ms - 3_600_000,
                    "resolvedAt": now_ms - 3_500_000,
                },
                {
                    "ruleId": rule_id,
                    "ruleName": "High error rate — gateway",
                    "state": "firing",
                    "value": 0.09,
                    "firedAt": now_ms - 1_800_000,
                },
            ]
        }
    }
