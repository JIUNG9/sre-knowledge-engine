"""Tests for :class:`scheduler.history.JobHistory`."""

from __future__ import annotations

from scheduler.history import JobHistory, JobRunRecord


def _record(job_id: str, started_at: str) -> JobRunRecord:
    return JobRunRecord(
        job_id=job_id,
        started_at=started_at,
        finished_at=started_at,
        duration_ms=10.0,
        outcome="success",
    )


def test_record_and_last_run() -> None:
    h = JobHistory()
    r = _record("a", "2026-04-21T00:00:00+00:00")
    h.record(r)
    assert h.last_run("a") is r
    assert h.last_run("b") is None


def test_ring_buffer_evicts_oldest() -> None:
    h = JobHistory(max_per_job=2)
    h.record(_record("a", "2026-04-21T00:00:00+00:00"))
    h.record(_record("a", "2026-04-21T00:01:00+00:00"))
    h.record(_record("a", "2026-04-21T00:02:00+00:00"))

    rows = h.list(job_id="a", limit=10)
    assert len(rows) == 2
    # Newest-first: 00:02 then 00:01.
    assert rows[0].started_at.endswith("00:02:00+00:00")
    assert rows[1].started_at.endswith("00:01:00+00:00")


def test_list_with_no_filter_merges_all_jobs() -> None:
    h = JobHistory()
    h.record(_record("a", "2026-04-21T00:00:00+00:00"))
    h.record(_record("b", "2026-04-21T00:01:00+00:00"))
    rows = h.list(limit=10)
    assert {r.job_id for r in rows} == {"a", "b"}
    # Newest first.
    assert rows[0].job_id == "b"


def test_list_limit_respected() -> None:
    h = JobHistory()
    for i in range(5):
        h.record(_record("a", f"2026-04-21T00:0{i}:00+00:00"))
    rows = h.list(job_id="a", limit=2)
    assert len(rows) == 2


def test_to_dict_round_trip() -> None:
    r = JobRunRecord(
        job_id="a",
        started_at="2026-04-21T00:00:00+00:00",
        outcome="failed",
        error="boom",
        detail={"x": 1},
    )
    d = r.to_dict()
    assert d["job_id"] == "a"
    assert d["outcome"] == "failed"
    assert d["error"] == "boom"
    assert d["detail"] == {"x": 1}
