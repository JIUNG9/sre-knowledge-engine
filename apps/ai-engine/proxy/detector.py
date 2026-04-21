# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""PII detection engine.

The detector is a pure-function, thread-safe class that accepts a string and
returns a list of :class:`Detection` objects describing every match. No
mutation of external state is performed — callers (typically
:class:`proxy.mapper.PlaceholderMapper`) are responsible for rewriting the
input.

Two backends are supported:

* **Regex** — always available, zero dependencies. Covers the categories
  required by Aegis Layer 0.1: emails, IPv4/IPv6, AWS account IDs,
  AWS access keys (AKIA*/ASIA*), internal hostnames (``*.internal``,
  ``*.local``, ``*.corp``, ``*.intranet``), JWT tokens, ``Bearer``
  tokens, and PEM blocks. Company-specific hostname suffixes (e.g.
  ``*.acme.internal``) are expected to be supplied via
  :attr:`PIIProxyConfig.custom_patterns` — the built-in list is
  intentionally generic so the proxy works the same way for every
  deployment.

* **Presidio** — optional. When
  `presidio-analyzer <https://microsoft.github.io/presidio/>`_ is installed
  we additionally run Microsoft's NER-assisted detector to catch
  person names, phone numbers, credit cards and other high-precision PII.

The two backends are merged and deduplicated in the ``hybrid`` provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal

# --------------------------------------------------------------------------- #
# Built-in regex patterns
# --------------------------------------------------------------------------- #

# NOTE: patterns are deliberately conservative. The consequence of a missed
# detection is a leaked value on the wire; the consequence of a false positive
# is a mangled placeholder in the prompt. We prefer specificity, and Presidio
# (when enabled) covers the long tail.

_PEM_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]+?-----[\s\S]+?-----END [A-Z ]+?-----",
    re.MULTILINE,
)

_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
)

_IPV4_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b"
)

# IPv6 is notoriously hard to match cleanly. We accept the two common forms:
#   1. Fully-specified form with 7 colons   -> 2001:0db8:85a3:0000:0000:8a2e:0370:7334
#   2. Compressed form containing "::"       -> 2001:db8:85a3::8a2e:370:7334
# We deliberately reject patterns that look like MAC addresses (six
# two-character hex groups separated by single colons) by requiring either
# ``::`` or >6 groups or at least one group of length != 2.
_IPV6_FULL_PATTERN = re.compile(
    r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b"
)
_IPV6_COMPRESSED_PATTERN = re.compile(
    r"(?<![A-Za-z0-9:])"
    r"(?:[A-Fa-f0-9]{1,4}:){1,7}:(?:[A-Fa-f0-9]{1,4}:){0,6}[A-Fa-f0-9]{1,4}"
    r"(?![A-Za-z0-9:])"
)

_AWS_ACCOUNT_PATTERN = re.compile(
    r"(?<![\d])(\d{12})(?![\d])"
)

_AWS_ACCESS_KEY_PATTERN = re.compile(
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
)

_INTERNAL_HOST_PATTERN = re.compile(
    r"\b[a-zA-Z0-9][a-zA-Z0-9_-]*"
    r"(?:\.[a-zA-Z0-9_-]+)*"
    r"\.(?:internal|local|corp|intranet|lan)\b",
    re.IGNORECASE,
)

# JWT: three base64url segments separated by dots.
_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]+?\.eyJ[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+\b"
)

# Bearer tokens in HTTP auth headers.
_BEARER_PATTERN = re.compile(
    r"(?<=Bearer )[A-Za-z0-9._~+/=\-]{12,}"
)

# Ordered highest-precedence first. Overlapping matches are resolved by
# the mapper in left-to-right order, so putting long composite patterns
# (PEM, JWT, email) before the atomic ones (ipv4, account id) prevents the
# atomic detectors from biting pieces out of them.
_BUILTIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PEM", _PEM_PATTERN),
    ("JWT", _JWT_PATTERN),
    ("BEARER", _BEARER_PATTERN),
    ("EMAIL", _EMAIL_PATTERN),
    ("AWS_KEY", _AWS_ACCESS_KEY_PATTERN),
    ("HOST", _INTERNAL_HOST_PATTERN),
    ("IPV6", _IPV6_FULL_PATTERN),
    ("IPV6", _IPV6_COMPRESSED_PATTERN),
    ("IPV4", _IPV4_PATTERN),
    ("AWS_ACCOUNT", _AWS_ACCOUNT_PATTERN),
]

# Presidio entity -> Aegis category mapping.
_PRESIDIO_ENTITY_MAP: dict[str, str] = {
    "PERSON": "PERSON",
    "PHONE_NUMBER": "PHONE",
    "CREDIT_CARD": "CC",
    "US_SSN": "SSN",
    "LOCATION": "LOCATION",
    "IBAN_CODE": "IBAN",
}


@dataclass(frozen=True)
class Detection:
    """A single PII hit inside a piece of text.

    Attributes:
        category: Short label identifying the kind of PII (``EMAIL``,
            ``IPV4``, ``AWS_ACCOUNT`` ...). Used as the placeholder prefix.
        start: Inclusive start index in the original string.
        end: Exclusive end index in the original string.
        value: The matched substring.
        source: Which backend produced the hit — ``"regex"``, ``"presidio"``,
            or ``"custom"``.
    """

    category: str
    start: int
    end: int
    value: str
    source: str


class PIIDetector:
    """Detect PII inside arbitrary strings.

    The detector is stateless and safe to share between threads. Each call
    to :meth:`detect` returns a freshly allocated, non-overlapping list of
    :class:`Detection` objects sorted by start offset.

    Args:
        provider: ``"regex"`` (default in regex-only builds), ``"presidio"``,
            or ``"hybrid"``. ``"hybrid"`` transparently degrades to regex when
            Presidio is not installed.
        custom_patterns: Extra regular expressions appended to the built-in
            set. Each is mapped to a ``CUSTOM`` category.
    """

    def __init__(
        self,
        provider: Literal["presidio", "regex", "hybrid"] = "hybrid",
        custom_patterns: Iterable[str] | None = None,
    ) -> None:
        self.provider = provider
        self._custom_patterns: list[re.Pattern[str]] = [
            re.compile(p, re.MULTILINE) for p in (custom_patterns or [])
        ]
        self._presidio = self._try_import_presidio() if provider != "regex" else None
        if provider == "presidio" and self._presidio is None:
            raise RuntimeError(
                "provider='presidio' requires `presidio-analyzer` to be installed; "
                "install the `presidio` extra or set provider='regex'."
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def detect(self, text: str) -> list[Detection]:
        """Return all PII detections found in ``text``.

        Overlapping regex and Presidio hits are merged: the longest match
        wins, and ties are broken by earlier start offset. The returned list
        is sorted ascending by ``start`` and contains no overlapping ranges.
        """
        if not text:
            return []

        hits: list[Detection] = []
        hits.extend(self._regex_hits(text))
        hits.extend(self._custom_hits(text))
        if self._presidio is not None:
            hits.extend(self._presidio_hits(text))

        return _merge_nonoverlapping(hits)

    # ------------------------------------------------------------------ #
    # Backends
    # ------------------------------------------------------------------ #
    def _regex_hits(self, text: str) -> list[Detection]:
        hits: list[Detection] = []
        for category, pattern in _BUILTIN_PATTERNS:
            for match in pattern.finditer(text):
                hits.append(
                    Detection(
                        category=category,
                        start=match.start(),
                        end=match.end(),
                        value=match.group(0),
                        source="regex",
                    )
                )
        return hits

    def _custom_hits(self, text: str) -> list[Detection]:
        hits: list[Detection] = []
        for pattern in self._custom_patterns:
            for match in pattern.finditer(text):
                hits.append(
                    Detection(
                        category="CUSTOM",
                        start=match.start(),
                        end=match.end(),
                        value=match.group(0),
                        source="custom",
                    )
                )
        return hits

    def _presidio_hits(self, text: str) -> list[Detection]:
        assert self._presidio is not None
        results = self._presidio.analyze(text=text, language="en")
        hits: list[Detection] = []
        for r in results:
            category = _PRESIDIO_ENTITY_MAP.get(r.entity_type)
            if category is None:
                continue
            hits.append(
                Detection(
                    category=category,
                    start=r.start,
                    end=r.end,
                    value=text[r.start : r.end],
                    source="presidio",
                )
            )
        return hits

    @staticmethod
    def _try_import_presidio():  # pragma: no cover - depends on optional dep
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore
        except ImportError:
            return None
        try:
            return AnalyzerEngine()
        except Exception:
            return None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _merge_nonoverlapping(hits: list[Detection]) -> list[Detection]:
    """Sort ``hits`` and drop any that overlap an earlier, longer hit.

    When two detections overlap we keep the longer one; on length tie we
    keep the earlier one. Ordering after filtering is ascending ``start``.
    """
    if not hits:
        return []

    # Sort so that for each start position the longest match comes first.
    hits_sorted = sorted(hits, key=lambda d: (d.start, -(d.end - d.start)))

    kept: list[Detection] = []
    cursor = -1
    for h in hits_sorted:
        if h.start >= cursor:
            kept.append(h)
            cursor = h.end
        else:
            # Overlaps the last kept hit. Keep whichever is longer.
            last = kept[-1]
            if (h.end - h.start) > (last.end - last.start):
                kept[-1] = h
                cursor = h.end
    return kept
