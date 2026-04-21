"""Sensitivity classifier for the Aegis LLM router.

The classifier answers a single question: *is it safe to send this
prompt to a cloud LLM?*

It returns one of three levels:

* ``sensitive``   — contains real prod data (hostnames, PII, known
                    customer names, large log payloads). **Must stay
                    local** under Korean PIPA Sep-2026 amendment.
* ``borderline``  — looks production-adjacent but not conclusive
                    (e.g. an AWS account ID without surrounding context).
                    Router treats borderline as sensitive by default
                    but surfaces signals so humans can review.
* ``sanitized``   — explicit placeholders (``<USER_1>``,
                    ``example.com``), or clearly public content
                    ("what is kubernetes?"). Safe to send to cloud.

The classifier is intentionally conservative: false-positives cost
latency and Ollama tokens; false-negatives cost PIPA fines. When in
doubt, call it sensitive.

The signals list is returned verbatim so the router can log it at
INFO for auditability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


Level = Literal["sensitive", "borderline", "sanitized"]


# --------------------------------------------------------------------------- #
# Regex patterns
# --------------------------------------------------------------------------- #

# Real-looking hostnames — FQDNs with a TLD that's not obviously an example.
# We explicitly allow example.com/example.org/localhost to be sanitized.
_EXAMPLE_TLDS = {"example", "test", "invalid", "localhost", "local"}
_HOSTNAME_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|dev|ai|co|kr|jp|us|cloud|app|internal|corp|local)\b"
)

# Kubernetes pod-style identifiers: service-abcdef-xyz12
_POD_RE = re.compile(r"\b[a-z][a-z0-9-]{2,}-[a-f0-9]{5,10}-[a-z0-9]{4,5}\b")

# AWS account IDs (12 digits, word-boundaried)
_AWS_ACCOUNT_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")

# AWS ARNs
_ARN_RE = re.compile(r"\barn:aws:[a-z0-9-]+:[a-z0-9-]*:\d{12}:[a-zA-Z0-9:/_.+-]+")

# Email addresses
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# IPv4 addresses — we exclude obvious RFC5737 test ranges (192.0.2/24, 198.51.100/24,
# 203.0.113/24) and link-local to avoid false positives on sanitized docs.
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SAFE_IP_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.", "0.0.0.", "127.0.0.")

# Credit card (rough Luhn-ish, 13-19 digits, possibly dashed/spaced)
_CC_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

# Korean resident registration number (주민등록번호) pattern
_KRN_RE = re.compile(r"\b\d{6}-[1-4]\d{6}\b")

# Bearer tokens / API keys (heuristic: long base64-ish string on a Bearer header)
_BEARER_RE = re.compile(r"\b(?:Bearer|Authorization:)\s+[A-Za-z0-9_\-.=/+]{20,}")

# Sanitized placeholder markers used by Aegis docs (and common in industry)
_SANITIZED_MARKER_RE = re.compile(
    r"<(?:USER|CUSTOMER|EMAIL|HOST|SERVICE|ACCOUNT|IP|TOKEN|REDACTED)_?\w*>"
    r"|\bREDACTED\b|\bXXXX+\b"
)

# Obviously sanitized / placeholder emails
_SANITIZED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "test.com"}


@dataclass
class Sensitivity:
    """Classification result."""

    level: Level
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_sensitive(self) -> bool:
        """True for sensitive or borderline — router treats both as local."""
        return self.level in ("sensitive", "borderline")


# --------------------------------------------------------------------------- #
# Classifier
# --------------------------------------------------------------------------- #


def _is_safe_email(addr: str) -> bool:
    _, _, domain = addr.partition("@")
    return domain.lower() in _SANITIZED_EMAIL_DOMAINS


def _is_safe_ip(ip: str) -> bool:
    return any(ip.startswith(p) for p in _SAFE_IP_PREFIXES)


def _looks_like_example_host(host: str) -> bool:
    parts = host.lower().split(".")
    # example.com, foo.example.com, localhost, etc.
    return any(p in _EXAMPLE_TLDS for p in parts) or "example" in parts


def classify_sensitivity(
    text: str,
    extra_keywords: list[str] | None = None,
    large_payload_threshold: int = 4000,
) -> Sensitivity:
    """Classify whether ``text`` contains sensitive production data.

    Args:
        text: Raw prompt content (user message, tool input, etc.).
        extra_keywords: Deployment-specific sensitive terms from config
            (company names, internal product codenames). Matched
            case-insensitively as substrings.
        large_payload_threshold: Character length above which the prompt
            is treated as a "large payload" and flagged borderline —
            real log dumps tend to be big, sanitized examples tend to
            be short.

    Returns:
        A :class:`Sensitivity` dataclass with level, signals, and
        confidence (0.0–1.0).
    """
    if not text or not text.strip():
        return Sensitivity(level="sanitized", signals=["empty"], confidence=1.0)

    signals: list[str] = []
    score = 0  # higher = more sensitive

    lowered = text.lower()

    # ---- Hard sensitive signals ------------------------------------------ #
    # PII: email addresses (excluding example.com)
    for email in _EMAIL_RE.findall(text):
        if not _is_safe_email(email):
            signals.append(f"email:{email}")
            score += 3
            break  # one is enough; don't leak more into logs

    # Korean resident registration number
    if _KRN_RE.search(text):
        signals.append("krn")
        score += 5

    # Credit-card-ish digits
    cc_match = _CC_RE.search(text)
    if cc_match:
        digits = re.sub(r"\D", "", cc_match.group(0))
        if 13 <= len(digits) <= 19:
            signals.append("credit_card_like")
            score += 4

    # Bearer tokens / authorization headers
    if _BEARER_RE.search(text):
        signals.append("auth_header")
        score += 4

    # AWS ARNs are unambiguous prod data
    if _ARN_RE.search(text):
        signals.append("aws_arn")
        score += 4

    # ---- Real hostnames -------------------------------------------------- #
    hosts = _HOSTNAME_RE.findall(text)
    real_hosts = [h for h in hosts if not _looks_like_example_host(h)]
    if real_hosts:
        signals.append(f"hostname:{real_hosts[0]}")
        score += 2

    # Kubernetes pod names
    if _POD_RE.search(text):
        signals.append("k8s_pod_id")
        score += 2

    # ---- Medium sensitive signals --------------------------------------- #
    # AWS account ID (12 digits)
    if _AWS_ACCOUNT_RE.search(text):
        signals.append("aws_account_id")
        score += 2

    # Non-test IPs — a public IPv4 in a prompt is a strong prod-data signal.
    for ip in _IPV4_RE.findall(text):
        if not _is_safe_ip(ip):
            signals.append(f"ip:{ip}")
            score += 2
            break

    # Deployment-specific keywords (your company name, customer codenames, etc.)
    if extra_keywords:
        for kw in extra_keywords:
            if kw and kw.lower() in lowered:
                signals.append(f"keyword:{kw}")
                score += 3

    # ---- Sanitization counter-signals ----------------------------------- #
    sanitized_markers = _SANITIZED_MARKER_RE.findall(text)
    if sanitized_markers:
        signals.append(f"sanitized_markers:{len(sanitized_markers)}")
        score -= 2  # clear intent to redact

    # Large payloads bump toward sensitive — real logs are big
    if len(text) >= large_payload_threshold:
        signals.append(f"large_payload:{len(text)}")
        score += 1

    # ---- Decision -------------------------------------------------------- #
    if score >= 4:
        level: Level = "sensitive"
        confidence = min(0.99, 0.7 + score * 0.05)
    elif score >= 2:
        level = "borderline"
        confidence = 0.6
    elif score <= -1:
        level = "sanitized"
        confidence = 0.9
    else:
        level = "sanitized"
        confidence = 0.8

    if not signals:
        signals.append("no_signals")

    return Sensitivity(level=level, signals=signals, confidence=confidence)
