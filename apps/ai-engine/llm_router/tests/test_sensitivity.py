"""Tests for the sensitivity classifier.

These fixtures are the source of truth for classifier precision. If
you loosen the classifier you *will* break these — that is intentional;
regulated-data routing changes should be reviewed carefully.
"""

from __future__ import annotations

import pytest

from llm_router.sensitivity import classify_sensitivity


# --------------------------------------------------------------------------- #
# Sensitive fixtures — must NOT leak to cloud
# --------------------------------------------------------------------------- #

SENSITIVE_FIXTURES: list[tuple[str, str]] = [
    (
        "real_email",
        "Investigate error from user alice.dev@acme-corp.com in production",
    ),
    (
        "real_hostname",
        "Pod on prod.api.acme-corp.com is returning 503",
    ),
    (
        "k8s_pod_id",
        "user-service-7fbd4c9f-xk2ps is OOM-killing every 10 minutes",
    ),
    (
        "aws_arn",
        "Policy arn:aws:iam::123456789012:role/prod-eks-node is too permissive",
    ),
    (
        "auth_header",
        "Request failed with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9xxxxxxxxxxxxx",
    ),
    (
        "aws_account_plus_hostname",
        "Account 987654321098 on eks-prod.internal is hitting a throttle",
    ),
    (
        "credit_card",
        "User report: transaction 4532-1234-5678-9010 was declined twice",
    ),
    (
        "krn",
        "Check ID 900101-1234567 against the audit log",
    ),
    (
        "company_keyword",
        "The acme-corp S3 bucket is misconfigured and public",
    ),
    (
        "real_ipv4",
        "Traffic from 52.78.112.45 is spiking our WAF",
    ),
    (
        "large_log_dump",
        "Here is the full error trace:\n" + ("2026-04-10 14:02:11 ERROR user-service pod=user-svc-abc123-zz99 " * 80),
    ),
]


@pytest.mark.parametrize("name,text", SENSITIVE_FIXTURES, ids=[n for n, _ in SENSITIVE_FIXTURES])
def test_sensitive_fixtures_are_classified_sensitive(name: str, text: str) -> None:
    result = classify_sensitivity(
        text,
        extra_keywords=["acme-corp", "customer-xyz"],
    )
    assert result.is_sensitive, (
        f"{name!r} should be sensitive/borderline but got {result.level}; "
        f"signals={result.signals}"
    )


# --------------------------------------------------------------------------- #
# Sanitized fixtures — safe to send to cloud
# --------------------------------------------------------------------------- #

SANITIZED_FIXTURES: list[tuple[str, str]] = [
    ("public_question", "What is kubernetes?"),
    ("generic_concept", "Explain the difference between SLO and SLA"),
    (
        "sanitized_markers",
        "User <USER_1> reported a timeout when contacting <SERVICE_2>",
    ),
    (
        "example_email",
        "Reach out to support@example.com for more info",
    ),
    (
        "example_host",
        "Navigate to https://app.example.com/settings",
    ),
    (
        "rfc5737_ip",
        "Use 192.0.2.1 as the gateway in your lab environment",
    ),
    (
        "redacted",
        "The employee REDACTED reported the bug, and host XXXXXXX was affected",
    ),
    (
        "generic_code",
        "How do I write a Python decorator that memoizes a function?",
    ),
    (
        "empty",
        "",
    ),
]


@pytest.mark.parametrize("name,text", SANITIZED_FIXTURES, ids=[n for n, _ in SANITIZED_FIXTURES])
def test_sanitized_fixtures_are_classified_sanitized(name: str, text: str) -> None:
    result = classify_sensitivity(text, extra_keywords=[])
    assert result.level == "sanitized", (
        f"{name!r} should be sanitized but got {result.level}; signals={result.signals}"
    )


# --------------------------------------------------------------------------- #
# Shape invariants
# --------------------------------------------------------------------------- #


def test_classifier_always_returns_signals_list() -> None:
    assert classify_sensitivity("hello world").signals  # at least "no_signals"


def test_classifier_is_sensitive_shortcut() -> None:
    s = classify_sensitivity("user@realcompany.co.kr had a 500 error")
    assert s.is_sensitive is True

    s2 = classify_sensitivity("what is TCP?")
    assert s2.is_sensitive is False


def test_extra_keywords_force_sensitive() -> None:
    # Without keyword — sanitized
    plain = classify_sensitivity("all systems are green")
    assert plain.level == "sanitized"

    # With keyword — sensitive
    kw = classify_sensitivity("all Acme systems are green", extra_keywords=["Acme"])
    assert kw.is_sensitive


def test_sanitized_markers_counteract_weak_signals() -> None:
    # An AWS account ID alone is borderline; a <REDACTED> marker should
    # not flip it sanitized but should suppress a lone IP hit.
    text = "Traffic from <IP_1> hit <SERVICE_2>"
    s = classify_sensitivity(text)
    assert s.level == "sanitized"
