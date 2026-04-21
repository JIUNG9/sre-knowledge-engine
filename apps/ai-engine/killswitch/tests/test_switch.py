"""Tests for ``killswitch.switch.KillSwitch`` using fakeredis."""

from __future__ import annotations

import json
from pathlib import Path

import fakeredis
import pytest

from killswitch.config import KillSwitchConfig
from killswitch.switch import KillSwitch


@pytest.fixture
def tmp_config(tmp_path: Path) -> KillSwitchConfig:
    return KillSwitchConfig(
        redis_url="redis://localhost:6379",
        backend="redis",
        audit_log_path=tmp_path / "audit.jsonl",
        file_backend_path=tmp_path / "killswitch.flag",
    )


@pytest.fixture
def fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def switch(
    tmp_config: KillSwitchConfig, fake_redis: fakeredis.FakeRedis
) -> KillSwitch:
    return KillSwitch.with_redis_client(fake_redis, tmp_config)


# ---------------------------------------------------------------------- #
# is_active / trip / release / status
# ---------------------------------------------------------------------- #


def test_switch_starts_clear(switch: KillSwitch) -> None:
    assert switch.is_active() is False
    status = switch.status()
    assert status.active is False
    assert status.backend == "redis"


def test_trip_sets_active_with_metadata(switch: KillSwitch) -> None:
    result = switch.trip(reason="db meltdown", operator="june.gu")
    assert result.active is True
    assert result.operator == "june.gu"
    assert result.reason == "db meltdown"
    assert result.tripped_at is not None

    assert switch.is_active() is True
    status = switch.status()
    assert status.active is True
    assert status.operator == "june.gu"
    assert status.reason == "db meltdown"


def test_release_clears_state(switch: KillSwitch) -> None:
    switch.trip(reason="test", operator="june.gu")
    assert switch.is_active() is True
    released = switch.release(operator="june.gu")
    assert released.active is False
    assert switch.is_active() is False


def test_trip_requires_reason_and_operator(switch: KillSwitch) -> None:
    with pytest.raises(ValueError):
        switch.trip(reason="", operator="june.gu")
    with pytest.raises(ValueError):
        switch.trip(reason="x", operator="")


def test_release_requires_operator(switch: KillSwitch) -> None:
    with pytest.raises(ValueError):
        switch.release(operator="")


def test_trip_is_idempotent(switch: KillSwitch) -> None:
    switch.trip(reason="first", operator="june.gu")
    switch.trip(reason="second", operator="pagerduty")
    status = switch.status()
    assert status.active is True
    # Most recent trip wins — this is intentional so repeat PagerDuty
    # webhooks cannot "hide" a more recent human trip.
    assert status.reason == "second"
    assert status.operator == "pagerduty"


def test_unstructured_redis_value_is_treated_as_active(
    switch: KillSwitch, fake_redis: fakeredis.FakeRedis, tmp_config: KillSwitchConfig
) -> None:
    """Covers the ``redis-cli SET aegis:killswitch 1`` case from KILLSWITCH.md."""
    fake_redis.set(tmp_config.state_key, "1")
    assert switch.is_active() is True
    status = switch.status()
    assert status.active is True
    assert status.reason == "unstructured state value"


# ---------------------------------------------------------------------- #
# Audit log
# ---------------------------------------------------------------------- #


def _read_audit(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_audit_log_records_trip_and_release(
    switch: KillSwitch, tmp_config: KillSwitchConfig
) -> None:
    switch.trip(reason="rca in progress", operator="june.gu")
    switch.release(operator="june.gu")

    entries = _read_audit(tmp_config.audit_log_path)
    events = [e["event"] for e in entries]
    assert events == ["trip", "release"]
    assert entries[0]["operator"] == "june.gu"
    assert entries[0]["reason"] == "rca in progress"
    assert entries[0]["backend"] == "redis"
    assert "timestamp" in entries[0]
    assert "pid" in entries[0]


def test_audit_log_is_append_only(
    switch: KillSwitch, tmp_config: KillSwitchConfig
) -> None:
    for i in range(5):
        switch.trip(reason=f"r{i}", operator="june.gu")
        switch.release(operator="june.gu")
    entries = _read_audit(tmp_config.audit_log_path)
    assert len(entries) == 10


# ---------------------------------------------------------------------- #
# File backend + graceful fallback
# ---------------------------------------------------------------------- #


def test_file_backend_roundtrip(tmp_path: Path) -> None:
    cfg = KillSwitchConfig(
        backend="file",
        audit_log_path=tmp_path / "audit.jsonl",
        file_backend_path=tmp_path / "ks.flag",
    )
    ks = KillSwitch(cfg)
    assert ks.backend == "file"
    assert ks.is_active() is False
    ks.trip(reason="no redis", operator="june.gu")
    assert ks.is_active() is True
    assert cfg.file_backend_path.exists()
    status = ks.status()
    assert status.operator == "june.gu"
    ks.release(operator="june.gu")
    assert not cfg.file_backend_path.exists()


def test_redis_unreachable_falls_back_to_file(tmp_path: Path) -> None:
    """If Redis rejects the initial ping we must degrade gracefully."""
    cfg = KillSwitchConfig(
        redis_url="redis://127.0.0.1:1",  # port 1 will refuse
        backend="redis",
        audit_log_path=tmp_path / "audit.jsonl",
        file_backend_path=tmp_path / "ks.flag",
    )
    ks = KillSwitch(cfg)
    assert ks.backend == "file"
    # The fallback itself is recorded in the audit log.
    entries = _read_audit(cfg.audit_log_path)
    assert any(e["event"] == "backend_fallback" for e in entries)


def test_is_active_performance_under_5ms(switch: KillSwitch) -> None:
    """Smoke-test the hot-path latency with fakeredis (should be trivial)."""
    import time

    # warmup
    switch.is_active()
    start = time.monotonic()
    for _ in range(100):
        switch.is_active()
    elapsed_ms = (time.monotonic() - start) * 1000 / 100
    # fakeredis in-process is orders of magnitude under 5ms; this asserts the
    # hot path does not accidentally grow a backend-probe on every call.
    assert elapsed_ms < 5
