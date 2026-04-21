# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0.
"""Reversibility and scoping tests for ``PlaceholderMapper``."""

from __future__ import annotations


import pytest

from proxy.detector import PIIDetector
from proxy.mapper import PlaceholderMapper


@pytest.fixture
def mapper() -> PlaceholderMapper:
    return PlaceholderMapper(ttl_seconds=3600)


@pytest.fixture
def detector() -> PIIDetector:
    return PIIDetector(provider="regex")


def test_round_trip_restores_original_text(
    mapper: PlaceholderMapper, detector: PIIDetector
) -> None:
    text = (
        "User alice.dev@acme-corp.com from 10.0.0.42 hit host "
        "db01.prod.internal in account 123456789012"
    )
    scope = mapper.new_scope()
    redacted = mapper.redact(scope, text, detector.detect(text))
    # Placeholders should have replaced the PII.
    assert "alice.dev@acme-corp.com" not in redacted
    assert "10.0.0.42" not in redacted
    assert "db01.prod.internal" not in redacted
    assert "123456789012" not in redacted
    # Round-trip via restore yields the original.
    assert mapper.restore(scope, redacted) == text


def test_duplicate_values_share_placeholder(
    mapper: PlaceholderMapper, detector: PIIDetector
) -> None:
    text = "10.0.0.1 talked to 10.0.0.1; also 10.0.0.2."
    scope = mapper.new_scope()
    redacted = mapper.redact(scope, text, detector.detect(text))
    # Two distinct IPs -> two distinct placeholders; duplicate collapses.
    assert redacted.count("<IPV4_1>") == 2
    assert redacted.count("<IPV4_2>") == 1


def test_scopes_are_isolated(
    mapper: PlaceholderMapper, detector: PIIDetector
) -> None:
    text = "value 10.0.0.1"
    a = mapper.new_scope()
    b = mapper.new_scope()
    red_a = mapper.redact(a, text, detector.detect(text))
    red_b = mapper.redact(b, text, detector.detect(text))
    # Same placeholder text, but different scopes own distinct mappings.
    assert "<IPV4_1>" in red_a and "<IPV4_1>" in red_b
    # Restoring scope-a's redaction with scope-b must still round-trip because
    # the strings are identical AND b has the same mapping for this value —
    # but only because b also saw it. If we drop b's scope, restoring there
    # leaves the placeholder untouched.
    mapper.drop_scope(b)
    assert mapper.restore(b, red_a) == red_a  # unknown scope: no-op
    assert mapper.restore(a, red_a) == text


def test_unknown_placeholder_left_intact(
    mapper: PlaceholderMapper, detector: PIIDetector
) -> None:
    scope = mapper.new_scope()
    # No detections; mapping is empty.
    text_with_placeholder = "Claude mentioned <HOST_99> spontaneously"
    restored = mapper.restore(scope, text_with_placeholder)
    assert restored == text_with_placeholder


def test_expired_scope_is_evicted(detector: PIIDetector) -> None:
    mapper = PlaceholderMapper(ttl_seconds=1)
    scope = mapper.new_scope()
    mapper.redact(scope, "10.0.0.1", detector.detect("10.0.0.1"))
    assert mapper.mapping(scope) != {}
    # Force expiry by rewinding the scope's birth.
    mapper._scopes[scope].created_at -= 10  # noqa: SLF001
    assert mapper.mapping(scope) == {}


def test_sweep_removes_expired_scopes() -> None:
    mapper = PlaceholderMapper(ttl_seconds=1)
    s1 = mapper.new_scope()
    s2 = mapper.new_scope()
    mapper._scopes[s1].created_at -= 10  # noqa: SLF001
    mapper._scopes[s2].created_at -= 10  # noqa: SLF001
    removed = mapper.sweep()
    assert removed == 2


def test_drop_scope_is_idempotent(mapper: PlaceholderMapper) -> None:
    scope = mapper.new_scope()
    mapper.drop_scope(scope)
    mapper.drop_scope(scope)  # must not raise
    assert mapper.mapping(scope) == {}


def test_redact_is_noop_when_no_detections(mapper: PlaceholderMapper) -> None:
    scope = mapper.new_scope()
    text = "no pii here"
    assert mapper.redact(scope, text, []) == text


def test_thread_safety_smoke() -> None:
    """Hammer the mapper from multiple threads; no exceptions, consistent map."""
    import threading

    mapper = PlaceholderMapper()
    detector = PIIDetector(provider="regex")
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(50):
                scope = mapper.new_scope()
                text = f"src=10.0.0.{1} user@acme-corp.com"
                red = mapper.redact(scope, text, detector.detect(text))
                assert mapper.restore(scope, red) == text
                mapper.drop_scope(scope)
        except BaseException as e:  # pragma: no cover - surfaced via assert below
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
