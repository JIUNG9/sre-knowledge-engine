"""Tests for :mod:`invalidation.resynth_queue`."""

from __future__ import annotations

from pathlib import Path

import pytest

from invalidation.resynth_queue import drain_resynth_queue, rotate_queue


pytestmark = pytest.mark.asyncio


def test_rotate_queue_returns_none_when_missing(tmp_path: Path) -> None:
    """A missing queue file is the steady state most of the time."""
    assert rotate_queue(tmp_path / "queue.txt") is None


def test_rotate_queue_returns_none_when_empty(tmp_path: Path) -> None:
    """Empty queue ⇒ skip the rename to avoid creating noise files."""
    queue = tmp_path / "queue.txt"
    queue.touch()
    assert rotate_queue(queue) is None


def test_rotate_queue_renames_atomically(tmp_path: Path) -> None:
    """A non-empty queue is moved to a uniquely-named processing file
    in the same directory, leaving the original path missing so the
    engine creates a fresh empty file on its next append."""
    queue = tmp_path / "queue.txt"
    queue.write_text("auth-service\nscaling-runbook\n", encoding="utf-8")
    rotated = rotate_queue(queue)

    assert rotated is not None
    assert rotated.exists()
    assert rotated.parent == tmp_path
    assert rotated.name.startswith("queue.txt.processing-")
    assert not queue.exists()
    assert (
        rotated.read_text(encoding="utf-8")
        == "auth-service\nscaling-runbook\n"
    )


async def test_drain_dedupes_and_calls_resynth(tmp_path: Path) -> None:
    """Repeated slugs in the queue collapse to one call per unique
    slug; ordering is first-seen for replay determinism."""
    queue = tmp_path / "queue.txt"
    queue.write_text(
        "auth-service\n"
        "auth-service\n"  # dup
        "scaling-runbook\n"
        "auth-service\n"  # dup again
        "\n"  # blank lines skipped
        "rate-limiter\n",
        encoding="utf-8",
    )

    seen: list[str] = []

    async def resynth(slug: str) -> None:
        seen.append(slug)

    summary = await drain_resynth_queue(queue, resynth)

    assert seen == ["auth-service", "scaling-runbook", "rate-limiter"]
    assert summary == {
        "rotated": True,
        "unique_slugs": 3,
        "ok": 3,
        "errors": 0,
    }
    # Rotated file gone after success; live queue not re-created.
    assert not queue.exists()


async def test_drain_handles_resynth_failures(tmp_path: Path) -> None:
    """A failing resynth_func for one slug must not block the others."""
    queue = tmp_path / "queue.txt"
    queue.write_text("good-1\nbad\ngood-2\n", encoding="utf-8")

    async def resynth(slug: str) -> None:
        if slug == "bad":
            raise RuntimeError("synthesis failed")

    summary = await drain_resynth_queue(queue, resynth)

    assert summary["unique_slugs"] == 3
    assert summary["ok"] == 2
    assert summary["errors"] == 1


async def test_drain_no_op_when_queue_missing(tmp_path: Path) -> None:
    """The drainer is run on a fixed interval; most ticks find an empty
    queue. No-op fast path must not raise or create artifacts."""

    async def resynth(slug: str) -> None:  # pragma: no cover - never called
        raise AssertionError("resynth must not run on empty queue")

    summary = await drain_resynth_queue(tmp_path / "queue.txt", resynth)
    assert summary == {
        "rotated": False,
        "unique_slugs": 0,
        "ok": 0,
        "errors": 0,
    }
