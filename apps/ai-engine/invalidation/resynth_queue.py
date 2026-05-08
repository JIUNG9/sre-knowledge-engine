"""Scheduler-side consumer of the resynth-hint queue.

The InvalidationEngine appends one slug per line to
``<vault_root>/_meta/resynth-queue.txt`` whenever a non-shadow event
flips a page to ``pending_revalidation``. This module turns those
hints into actual re-synthesis calls.

Concurrency model
-----------------
The engine is append-only on the live queue file. The drainer
*rotates* (renames atomically) the live file to a uniquely-named
processing file, then reads the rotated file at leisure. The engine,
running in its own asyncio task, sees the original path missing on
its next ``open(... "a")`` call and creates a fresh empty file. New
events from that point on accumulate in the new live file; we
process the rotated batch independently.

This is the same pattern syslog rotators use: the writer never
blocks on the reader, and a single rename is the entire critical
section. We're explicitly single-process so we don't need flock.

Interface
---------
- :func:`rotate_queue` — atomic rename, returns the rotated Path or
  None if the queue is empty / missing.
- :func:`drain_resynth_queue` — rotate + read + dedupe + call
  ``resynth_func`` once per unique slug + unlink rotated file.

The ``resynth_func`` is injected so this module stays free of any
WikiEngine dependency. ``main.py`` (or a test) binds it to whatever
re-synthesis path the deployment uses.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from .metrics import _meter

logger = logging.getLogger("aegis.invalidation.resynth")

# Counter so operators can dashboard "what is the scheduler actually
# doing?" — separate from the engine-side records counter, because
# multiple drains can collapse to one resynth (dedup) and a single
# engine record can split across multiple drains (queue rotation).
_RESYNTH_DRAINED_TOTAL = _meter.create_counter(
    name="aegis_resynth_drained_total",
    unit="1",
    description=(
        "Count of unique slugs the scheduler resynth drainer has "
        "passed to the resynth_func. Attributes: outcome (ok|error)."
    ),
)


ResynthFunc = Callable[[str], Awaitable[None]]


def rotate_queue(queue_path: Path) -> Path | None:
    """Atomically rename ``queue_path`` to a processing path.

    Returns the rotated Path if the rename happened, ``None`` if the
    file was missing or empty.

    The rotated filename embeds a monotonic-ish timestamp so concurrent
    drains (they shouldn't happen — single-process — but defense in
    depth) don't collide. We use ``time.time_ns()`` because it's
    monotonically growing across normal clock skews.
    """

    if not queue_path.exists():
        return None
    # Stat-then-rename is racy with concurrent writers, but the engine
    # only appends, never truncates. An empty file at stat time stays
    # empty through the rename — worth the cheap branch to avoid
    # creating processing files for no reason.
    if queue_path.stat().st_size == 0:
        return None

    rotated = queue_path.with_suffix(
        queue_path.suffix + f".processing-{time.time_ns()}"
    )
    os.replace(queue_path, rotated)
    return rotated


async def drain_resynth_queue(
    queue_path: Path,
    resynth_func: ResynthFunc,
) -> dict[str, int]:
    """Drain ``queue_path`` once. Idempotent and crash-safe.

    Returns a small summary dict suitable for the scheduler's run-history
    detail field:
        {"rotated": bool, "unique_slugs": N, "ok": N, "errors": N}

    Per-slug exceptions from ``resynth_func`` are caught and logged.
    The rotated file is unlinked only after every slug has been
    attempted, even if some failed — re-running this drainer wouldn't
    retry the failures (the rotated file is gone), but the engine is
    likely to fire fresh events for the same artifacts soon, which
    re-enqueues the affected slugs naturally. Operators see the failure
    count in the run-history detail and can investigate.
    """

    rotated = rotate_queue(queue_path)
    if rotated is None:
        return {"rotated": False, "unique_slugs": 0, "ok": 0, "errors": 0}

    raw = rotated.read_text(encoding="utf-8").splitlines()
    # Preserve first-seen order while dedup'ing — replay determinism is
    # nice-to-have for incident triage even though semantics don't depend
    # on it.
    seen: dict[str, None] = {}
    for line in raw:
        slug = line.strip()
        if slug and slug not in seen:
            seen[slug] = None
    unique_slugs = list(seen)

    ok = 0
    errors = 0
    for slug in unique_slugs:
        try:
            await resynth_func(slug)
        except Exception:  # noqa: BLE001
            errors += 1
            _RESYNTH_DRAINED_TOTAL.add(1, {"outcome": "error"})
            logger.exception("resynth_func failed for slug %s", slug)
        else:
            ok += 1
            _RESYNTH_DRAINED_TOTAL.add(1, {"outcome": "ok"})

    rotated.unlink(missing_ok=True)
    logger.info(
        "resynth drain: %d slugs, %d ok, %d errors",
        len(unique_slugs),
        ok,
        errors,
    )
    return {
        "rotated": True,
        "unique_slugs": len(unique_slugs),
        "ok": ok,
        "errors": errors,
    }
