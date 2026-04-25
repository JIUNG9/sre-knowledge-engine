"""Tests for :mod:`scheduler.runner` — the safety wrapper.

Verified behaviors:
- Kill switch active -> the work function is NEVER awaited; record
  outcome is ``skipped``.
- Kill switch read raises -> degrade to ``proceed`` and log.
- Job func raises -> outcome is ``failed``, error is preserved, scheduler
  is not killed.
- OTel span carries the documented attributes.
- Duration is recorded in milliseconds.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from scheduler.history import JobHistory
from scheduler.jobs import Job
from scheduler.runner import JobRunner, run_with_safety


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_job(func, *, job_id: str = "test_job", interval: int = 60) -> Job:
    return Job(
        id=job_id,
        name="Test Job",
        interval_seconds=interval,
        func=func,
        metadata={"connector": "test"},
    )


# --------------------------------------------------------------------------- #
# Kill switch
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_killswitch_active_skips_func(tripped_killswitch) -> None:
    func = AsyncMock(return_value={"ok": True})
    history = JobHistory()
    runner = JobRunner(history, killswitch=tripped_killswitch)

    record = await runner.run_once(_make_job(func))

    assert record.outcome == "skipped"
    assert record.detail["reason"] == "killswitch_active"
    func.assert_not_awaited()
    assert tripped_killswitch.calls == 1


@pytest.mark.asyncio
async def test_killswitch_clear_proceeds(fake_killswitch) -> None:
    func = AsyncMock(return_value={"pages": 3})
    history = JobHistory()
    runner = JobRunner(history, killswitch=fake_killswitch)

    record = await runner.run_once(_make_job(func))

    assert record.outcome == "success"
    assert record.detail["pages"] == 3
    func.assert_awaited_once()


@pytest.mark.asyncio
async def test_killswitch_read_failure_does_not_block_run() -> None:
    """If the kill switch backend errors, we proceed (fail-safe) and log."""
    from scheduler.tests.conftest import FakeKillSwitch

    flaky = FakeKillSwitch(active=True, raise_on_check=True)
    func = AsyncMock(return_value={"ok": True})
    history = JobHistory()
    runner = JobRunner(history, killswitch=flaky)

    record = await runner.run_once(_make_job(func))

    # Read raised -> proceed (graceful degradation), not skip.
    assert record.outcome == "success"
    func.assert_awaited_once()


# --------------------------------------------------------------------------- #
# Exception isolation
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_exception_in_func_records_failed_but_does_not_raise() -> None:
    boom = AsyncMock(side_effect=RuntimeError("connector dead"))
    history = JobHistory()
    runner = JobRunner(history)

    record = await runner.run_once(_make_job(boom, job_id="boom_job"))

    assert record.outcome == "failed"
    assert "connector dead" in (record.error or "")
    assert history.last_run("boom_job") is record


@pytest.mark.asyncio
async def test_two_failures_in_a_row_do_not_compound() -> None:
    """Failed runs are independent — runner state must not be sticky."""
    boom = AsyncMock(side_effect=ValueError("fail"))
    history = JobHistory()
    runner = JobRunner(history)

    job = _make_job(boom)
    r1 = await runner.run_once(job)
    r2 = await runner.run_once(job)

    assert r1.outcome == "failed"
    assert r2.outcome == "failed"
    assert len(history.list(job_id=job.id)) == 2


# --------------------------------------------------------------------------- #
# History + duration
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_run_record_captures_duration_and_timestamps() -> None:
    func = AsyncMock(return_value={"ok": True})
    history = JobHistory()
    runner = JobRunner(history)

    record = await runner.run_once(_make_job(func))

    assert record.started_at is not None
    assert record.finished_at is not None
    assert record.duration_ms is not None
    assert record.duration_ms >= 0


@pytest.mark.asyncio
async def test_module_level_run_with_safety_helper() -> None:
    func = AsyncMock(return_value={"ok": True})
    history = JobHistory()

    record = await run_with_safety(_make_job(func), history=history)

    assert record.outcome == "success"
    assert history.last_run("test_job") is record


# --------------------------------------------------------------------------- #
# OTel span attributes
# --------------------------------------------------------------------------- #


def _install_in_memory_exporter():
    """Install (or reuse) an in-memory exporter on the global TracerProvider.

    OTel's API forbids overriding an already-set TracerProvider, so once
    one test in the suite has installed one, subsequent tests must
    attach their exporter to that same provider. We detect the case
    and append rather than replace.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@pytest.mark.asyncio
async def test_otel_span_carries_job_attributes() -> None:
    """Capture spans via an in-memory exporter and assert key attrs."""
    exporter = _install_in_memory_exporter()

    func = AsyncMock(return_value={"ok": True})
    history = JobHistory()
    runner = JobRunner(history)

    job = _make_job(func, job_id="otel_job", interval=300)
    job.metadata["lookback_minutes"] = 60
    await runner.run_once(job)

    spans = [s for s in exporter.get_finished_spans() if s.name == "aegis.scheduler.job"]
    matching = [
        s for s in spans
        if dict(s.attributes or {}).get("aegis.job.id") == "otel_job"
    ]
    assert matching, f"no aegis.scheduler.job span for otel_job (got {[s.attributes for s in spans]})"
    attrs = dict(matching[-1].attributes or {})
    assert attrs["aegis.job.id"] == "otel_job"
    assert attrs["aegis.job.name"] == "Test Job"
    assert attrs["aegis.job.interval_minutes"] == 5.0
    assert attrs["aegis.job.outcome"] == "success"
    assert attrs["aegis.job.meta.connector"] == "test"
    assert attrs["aegis.job.meta.lookback_minutes"] == 60


@pytest.mark.asyncio
async def test_otel_span_marks_failed_status_on_exception() -> None:
    from opentelemetry.trace import StatusCode

    exporter = _install_in_memory_exporter()

    boom = AsyncMock(side_effect=RuntimeError("nope"))
    history = JobHistory()
    runner = JobRunner(history)

    await runner.run_once(_make_job(boom, job_id="bad"))

    spans = [s for s in exporter.get_finished_spans() if s.name == "aegis.scheduler.job"]
    matching = [
        s for s in spans
        if dict(s.attributes or {}).get("aegis.job.id") == "bad"
    ]
    assert matching, "no failed-job span captured"
    span = matching[-1]
    assert span.status.status_code == StatusCode.ERROR
    assert dict(span.attributes or {})["aegis.job.outcome"] == "failed"
