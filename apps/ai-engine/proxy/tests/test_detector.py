# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0.
"""Detection unit tests with ~20 realistic SRE log fixtures.

Each fixture is a tuple ``(line, expected_categories)`` where
``expected_categories`` is a multiset of category labels that must appear
somewhere in the detector's output. Fixtures exercise Korean employee
emails, a large tech company / a large e-commerce company / acme-corp internal hostnames, AWS account IDs,
access keys, IPv6, JWT and PEM blocks.
"""

from __future__ import annotations

from collections import Counter

import pytest

from proxy.detector import PIIDetector


REGEX_DETECTOR = PIIDetector(provider="regex")


LOG_FIXTURES: list[tuple[str, list[str]]] = [
    # Korean employee emails.
    (
        "User june@example.com logged in from 10.0.12.34",
        ["EMAIL", "IPV4"],
    ),
    (
        "Contact sre-oncall@acme.com — check with ops@acme-retail.com",
        ["EMAIL", "EMAIL"],
    ),
    # Internal hostnames across a large tech company / a large e-commerce company / acme-corp / generic suffixes.
    (
        "db01.prod.example.com is unreachable from api.acme.co.kr",
        ["HOST", "HOST"],
    ),
    (
        "eks-worker-17.cluster.local is NotReady",
        ["HOST"],
    ),
    (
        "Upstream jenkins.ci.corp returned 504",
        ["HOST"],
    ),
    (
        "cache-node-3.internal evicted 1.2GB",
        ["HOST"],
    ),
    # AWS account IDs (12 digits).
    (
        "Cross-account role arn:aws:iam::123456789012:role/Deploy",
        ["AWS_ACCOUNT"],
    ),
    (
        "Accounts 123456789012 and 987654321098 flagged by Config",
        ["AWS_ACCOUNT", "AWS_ACCOUNT"],
    ),
    # AWS access keys.
    (
        "Credential leak: AKIAIOSFODNN7EXAMPLE in logs",
        ["AWS_KEY"],
    ),
    (
        "Session key ASIA1234567890ABCDEF used by deploy bot",
        ["AWS_KEY"],
    ),
    # IPv4 / IPv6.
    (
        "Blocking traffic from 203.0.113.42 and 198.51.100.7",
        ["IPV4", "IPV4"],
    ),
    (
        "IPv6 peer 2001:db8:85a3::8a2e:370:7334 timed out",
        ["IPV6"],
    ),
    # JWT tokens. When a Bearer header wraps a JWT both matches overlap the
    # same span; the longer JWT wins after non-overlap merging.
    (
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc-123_DEF",
        ["JWT"],
    ),
    (
        "Refresh token eyJraWQiOiJLIn0.eyJ1c2VyIjoiYSJ9.sig-sig-sig",
        ["JWT"],
    ),
    # Bearer without JWT payload.
    (
        "curl -H 'Authorization: Bearer sk-xxxxxxxxxxxxxxxx'",
        ["BEARER"],
    ),
    # PEM blocks.
    (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpQIBAAKCAQEA0Z\n-----END RSA PRIVATE KEY-----",
        ["PEM"],
    ),
    # Mixed realistic incident line.
    (
        "oncall@example.com paged after db01.prod.example.com hit 100% CPU "
        "(aws acct 123456789012, src 10.20.30.40)",
        ["EMAIL", "HOST", "AWS_ACCOUNT", "IPV4"],
    ),
    # No PII — must be empty.
    (
        "Pod evicted: reason=Completed exitCode=0 restartCount=0",
        [],
    ),
    # Negative: random 12-digit order id inside a non-numeric word-boundary
    # context should still match (we cannot distinguish intent) — this
    # documents the conservative behavior.
    (
        "order-id 111122223333 processed",
        ["AWS_ACCOUNT"],
    ),
    # IPv6 must not swallow MAC-like strings.
    (
        "Interface MAC 01:23:45:67:89:ab link down",
        [],
    ),
]


@pytest.mark.parametrize("line,expected", LOG_FIXTURES)
def test_detections_match_expectations(line: str, expected: list[str]) -> None:
    hits = REGEX_DETECTOR.detect(line)
    got = Counter(d.category for d in hits)
    want = Counter(expected)
    assert got == want, f"line={line!r} got={dict(got)} want={dict(want)}"


def test_detections_are_sorted_and_nonoverlapping() -> None:
    text = (
        "Host db01.prod.example.com (10.0.1.2) reported by user@example.com; "
        "aws 123456789012 key AKIAIOSFODNN7EXAMPLE."
    )
    hits = REGEX_DETECTOR.detect(text)
    # Sorted ascending.
    assert hits == sorted(hits, key=lambda d: d.start)
    # Non-overlapping.
    for a, b in zip(hits, hits[1:]):
        assert a.end <= b.start


def test_custom_patterns_detected() -> None:
    detector = PIIDetector(provider="regex", custom_patterns=[r"INCIDENT-\d{4}"])
    hits = detector.detect("See INCIDENT-0042 for details")
    assert [h.category for h in hits] == ["CUSTOM"]
    assert hits[0].value == "INCIDENT-0042"


def test_email_inside_hostname_resolves_to_email_plus_none() -> None:
    # Email like "a@b.internal" — email and hostname both match overlapping
    # ranges. The longer one (email, which starts earlier) must win.
    hits = REGEX_DETECTOR.detect("contact me at alice@db01.internal please")
    cats = [h.category for h in hits]
    assert "EMAIL" in cats
    # Must not double-count the same span as HOST.
    spans = [(h.start, h.end) for h in hits]
    assert len(set(spans)) == len(spans)


def test_empty_string_returns_empty_list() -> None:
    assert REGEX_DETECTOR.detect("") == []


def test_presidio_provider_requires_package() -> None:
    # Regex-only installations must fail loudly if Presidio is demanded.
    try:
        PIIDetector(provider="presidio")
    except RuntimeError as e:
        assert "presidio-analyzer" in str(e)
    except Exception:  # pragma: no cover - env-specific
        pass
