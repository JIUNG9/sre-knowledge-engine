"""Tests for :mod:`scheduler.config` — env-driven configuration.

Verifies:
- Defaults: scheduler disabled, four built-in jobs at documented intervals.
- ``AEGIS_SCHEDULER_ENABLED`` truthy synonyms (``1``, ``true``, ``yes``).
- Per-job interval + enabled overrides land on the right ``JobConfig``.
- Invalid integers fall back to the documented default.
"""

from __future__ import annotations

import pytest

from scheduler.config import JobConfig, SchedulerConfig


def test_defaults_disable_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("AEGIS_SCHEDULER_"):
            monkeypatch.delenv(key, raising=False)

    cfg = SchedulerConfig.from_env()
    assert cfg.enabled is False
    assert set(cfg.jobs) == {
        "confluence_sync",
        "signoz_sync",
        "staleness_lint",
        "doc_reconciliation",
    }
    assert cfg.jobs["confluence_sync"].interval_seconds == 60 * 60
    assert cfg.jobs["signoz_sync"].interval_seconds == 15 * 60
    assert cfg.jobs["staleness_lint"].interval_seconds == 24 * 60 * 60
    assert cfg.jobs["doc_reconciliation"].interval_seconds == 12 * 60 * 60


@pytest.mark.parametrize("flag", ["1", "true", "yes", "on", "TRUE"])
def test_enabled_synonyms(
    flag: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AEGIS_SCHEDULER_ENABLED", flag)
    cfg = SchedulerConfig.from_env()
    assert cfg.enabled is True


@pytest.mark.parametrize("flag", ["", "0", "false", "no", "off", "garbage"])
def test_disabled_synonyms(
    flag: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AEGIS_SCHEDULER_ENABLED", flag)
    cfg = SchedulerConfig.from_env()
    assert cfg.enabled is False


def test_per_job_interval_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_SCHEDULER_ENABLED", "1")
    monkeypatch.setenv("AEGIS_SCHEDULER_CONFLUENCE_MINUTES", "5")
    monkeypatch.setenv("AEGIS_SCHEDULER_SIGNOZ_MINUTES", "1")

    cfg = SchedulerConfig.from_env()
    assert cfg.jobs["confluence_sync"].interval_seconds == 300
    assert cfg.jobs["signoz_sync"].interval_seconds == 60


def test_per_job_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_SCHEDULER_ENABLED", "1")
    monkeypatch.setenv("AEGIS_SCHEDULER_SIGNOZ_ENABLED", "0")

    cfg = SchedulerConfig.from_env()
    assert cfg.jobs["signoz_sync"].enabled is False
    assert cfg.jobs["confluence_sync"].enabled is True


def test_invalid_int_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_SCHEDULER_CONFLUENCE_MINUTES", "not-a-number")
    cfg = SchedulerConfig.from_env()
    assert cfg.jobs["confluence_sync"].interval_seconds == 60 * 60


def test_max_history_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_SCHEDULER_MAX_HISTORY", "500")
    cfg = SchedulerConfig.from_env()
    assert cfg.max_history == 500


def test_jobconfig_defaults() -> None:
    """Construction without args is documented for tests / fixtures."""
    jc = JobConfig(id="x")
    assert jc.enabled is True
    assert jc.interval_seconds == 3600
