"""Invalidation engine — Layer 1.6.

The engine fans out :class:`StateChangeEvent` from Layer 1.5 consumers
to dependent wiki pages and marks them ``pending_revalidation``.

Pattern: Truth Maintenance System (Doyle 1979). A page's claims have
*justifications* — references to external infra artifacts. When a
justification changes, every claim that depended on it becomes
suspect; a follow-up scheduler tick re-synthesizes the page.

Crash policy mirrors the rest of Aegis: an exception handling one
event is logged and the loop continues. A bad page mutation must not
abort the entire stream.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from state_subscription.models import StateChangeEvent

from .dependency_index import DependencyIndex
from .metrics import record_conflict, record_invalidation
from .models import InvalidationRecord

logger = logging.getLogger("aegis.invalidation")


# Mirror the wiki package's vault layout — pages live one of these dirs.
_PAGE_TYPE_DIRS: tuple[str, ...] = (
    "entities",
    "concepts",
    "incidents",
    "runbooks",
)


def _coerce_datetime(value: object) -> datetime | None:
    """Best-effort parse of a frontmatter datetime field.

    YAML may surface the value as a real :class:`datetime`, an ISO
    string, or ``None``. We accept all three and normalize to a
    timezone-aware UTC datetime. Anything we cannot parse becomes
    ``None`` — the caller treats that as "no last-seen".
    """

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


class InvalidationEngine:
    """Drains consumer streams, marks dependent pages, writes audit log.

    Lifespan: typically one engine per ai-engine process. The engine
    holds a reference to a :class:`DependencyIndex` and the vault root.
    It does NOT own the :class:`WikiEngine` — by design, invalidation
    only *marks* pages; resynthesis is the scheduler's job.
    """

    DEFAULT_PER_EVENT_FANOUT_CAP: int = 1000

    def __init__(
        self,
        vault_root: Path,
        index: DependencyIndex,
        log_path: Path | None = None,
        shadow_mode: bool = False,
        fanout_cap: int | None = None,
        resynth_queue_path: Path | None = None,
    ) -> None:
        """Args:

        vault_root: Vault directory. Page files live in
            ``<vault_root>/<entities|concepts|incidents|runbooks>/<slug>.md``.
        index: Pre-built :class:`DependencyIndex`. The caller is
            responsible for keeping it in sync with the vault — the
            engine does not rebuild it on its own.
        log_path: Override for the JSONL audit log location.
            Defaults to ``<vault_root>/_meta/invalidation-log.jsonl``.
        shadow_mode: When True, the engine logs every record but never
            mutates pages. Useful as a canary while integrating Layer 1.6
            against a busy production vault.
        fanout_cap: Hard upper bound on the number of slugs marked per
            event. A massive Terraform apply touching 200 resources
            could theoretically fan out to thousands of pages; the cap
            stops the engine from melting under that load. Defaults to
            :attr:`DEFAULT_PER_EVENT_FANOUT_CAP` (1000). The dropped
            slugs are recovered by the daily reconciliation pass
            (design doc §7 Burst overload).
        resynth_queue_path: File the engine appends pending slugs to so
            the scheduler can pick them up on its next tick. Defaults
            to ``<vault_root>/_meta/resynth-queue.txt``. The scheduler
            owns truncation of the queue after it consumes; the engine
            is append-only.
        """

        self.vault_root = Path(vault_root)
        self.index = index
        self.log_path = log_path or (
            self.vault_root / "_meta" / "invalidation-log.jsonl"
        )
        self.shadow_mode = shadow_mode
        self.fanout_cap = fanout_cap or self.DEFAULT_PER_EVENT_FANOUT_CAP
        self.resynth_queue_path = resynth_queue_path or (
            self.vault_root / "_meta" / "resynth-queue.txt"
        )
        self._log_lock = asyncio.Lock()
        self._resynth_lock = asyncio.Lock()
        # Per-slug last_updated we last observed. Used to detect human
        # edits between our writes — if the on-disk last_updated is
        # newer than what we recorded, a concurrent edit happened and we
        # skip the rewrite (operator's edit wins, per design doc §7).
        self._last_seen: dict[str, datetime] = {}

    # -- Public API ---------------------------------------------------- #

    async def consume(self, events: AsyncIterator[StateChangeEvent]) -> None:
        """Long-running task: drain one consumer's stream.

        Wrap the call site in :func:`asyncio.create_task` per consumer
        so they fan out independently. We swallow per-event exceptions
        so a single bad event can't cancel the whole task.
        """

        async for event in events:
            try:
                await self.handle_event(event)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "invalidation: handle_event failed for %s",
                    event.artifact_id,
                )

    async def consume_with_batching(
        self,
        events: AsyncIterator[StateChangeEvent],
        *,
        batch_window: float = 0.1,
    ) -> None:
        """Drain ``events`` and collapse arrivals within ``batch_window``
        seconds into a single fan-out per artifact_id.

        Why batch: a flapping ConfigMap can fire six events in under a
        second. Without batching we'd serialize six page-rewrites for
        each dependent slug. With batching we dedupe by ``artifact_id``
        (last event wins) and rewrite once per window. Design doc §5.

        The first event opens the window; subsequent events extend the
        batch but not the deadline — windows do not chain. When the
        deadline elapses (or the stream ends), the batch fans out and
        the next event opens a fresh window.

        Per-event exceptions are logged and the loop continues, same
        crash policy as :meth:`consume`. Stream termination flushes the
        in-flight batch before returning.
        """

        iterator = events.__aiter__()
        loop = asyncio.get_running_loop()
        while True:
            try:
                first = await iterator.__anext__()
            except StopAsyncIteration:
                return

            batch: dict[str, StateChangeEvent] = {first.artifact_id: first}
            deadline = loop.time() + batch_window
            stream_done = False
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    nxt = await asyncio.wait_for(
                        iterator.__anext__(), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    break
                except StopAsyncIteration:
                    stream_done = True
                    break
                # Coalesce by artifact: last event wins. The old value
                # of an earlier event becomes irrelevant — the engine
                # marks slugs pending regardless of value, only the
                # audit log cares which value flipped.
                batch[nxt.artifact_id] = nxt

            await self._fanout_batch(batch)
            if stream_done:
                return

    async def _fanout_batch(
        self, batch: dict[str, StateChangeEvent]
    ) -> None:
        """Run :meth:`handle_event` for every entry in ``batch``.

        Failures on one artifact must not block the others; mirror the
        per-event exception swallow pattern from :meth:`consume`.
        """

        for ev in batch.values():
            try:
                await self.handle_event(ev)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "invalidation: batched handle_event failed for %s",
                    ev.artifact_id,
                )

    async def handle_event(
        self, event: StateChangeEvent
    ) -> InvalidationRecord:
        """Process one event end-to-end.

        Steps:
            1. Look up dependents in the index.
            2. Build the :class:`InvalidationRecord`.
            3. Mutate every dependent page (skipped in shadow mode).
            4. Append the record to the audit log.

        The record is returned so callers can correlate against test
        assertions or audit reports. We intentionally write the log
        even when ``affected_slugs`` is empty — "we saw the change and
        nothing depended on it" is itself a meaningful audit fact.
        """

        slugs = await self.index.lookup(event.artifact_id)
        reason = "first_observation" if event.old_value is None else "value_change"
        # Per-event fanout cap. A massive Terraform apply that touches
        # 200 resources could fan out to tens of thousands of slugs in a
        # single tick. We process at most fanout_cap slugs synchronously
        # and let the daily reconciler pick up the dropped tail (design
        # doc §7). Sorting before slicing makes the cap deterministic
        # for tests and keeps the same prefix marked across replays.
        all_affected = sorted(slugs)
        truncated = len(all_affected) > self.fanout_cap
        affected = all_affected[: self.fanout_cap]
        record = InvalidationRecord(
            artifact_id=event.artifact_id,
            affected_slugs=affected,
            reason=reason,
            old_value=event.old_value,
            new_value=event.new_value,
            shadow_mode=self.shadow_mode,
            truncated=truncated,
            total_dependents=len(all_affected),
        )

        if truncated:
            logger.warning(
                "invalidation: fanout for %s truncated %d -> %d "
                "(reconciliation will sweep the tail)",
                event.artifact_id,
                len(all_affected),
                self.fanout_cap,
            )

        if not self.shadow_mode:
            for slug in record.affected_slugs:
                await self._mark_pending(slug)
            await self._enqueue_resynth(record.affected_slugs)

        await self._append_log(record)
        record_invalidation(
            shadow=self.shadow_mode,
            reason=reason,
            pages_marked=(
                0 if self.shadow_mode else len(record.affected_slugs)
            ),
            truncated=truncated,
        )
        return record

    # -- Internals ----------------------------------------------------- #

    async def _mark_pending(self, slug: str) -> None:
        """Set ``freshness=pending_revalidation`` on the page file.

        Writes ``last_invalidation_at`` so an operator can see how
        stale the pending mark is. If the page file isn't found we
        log a warning and continue — the index can be slightly out of
        date if a page was just deleted.

        Concurrency: a human may edit the page in their editor while
        the engine is mid-burst. We read ``last_updated`` first; if it
        is newer than the engine's last-seen value, a concurrent edit
        happened and we skip this rewrite (operator wins, design §7).
        Otherwise we write atomically via tempfile + os.replace so a
        crash mid-write cannot leave a torn file.
        """

        page_path = self._find_page_file(slug)
        if page_path is None or not page_path.exists():
            logger.warning(
                "invalidation: page file not found for slug %s; skipping mark",
                slug,
            )
            return

        post = frontmatter.load(str(page_path))
        on_disk_updated = _coerce_datetime(post.get("last_updated"))
        last_seen = self._last_seen.get(slug)
        if (
            last_seen is not None
            and on_disk_updated is not None
            and on_disk_updated > last_seen
        ):
            logger.warning(
                "invalidation: concurrent edit detected on %s "
                "(disk=%s, last_seen=%s); skipping rewrite",
                slug,
                on_disk_updated.isoformat(),
                last_seen.isoformat(),
            )
            record_conflict()
            # Refresh last-seen so the next event doesn't keep flagging.
            self._last_seen[slug] = on_disk_updated
            return

        post["freshness"] = "pending_revalidation"
        now = datetime.now(timezone.utc)
        post["last_invalidation_at"] = now.isoformat()
        self._atomic_write(page_path, frontmatter.dumps(post))
        # The engine just touched the file; record what we wrote so the
        # next conflict check compares against our own write, not the
        # synthesizer's previous one.
        post_updated = _coerce_datetime(post.get("last_updated"))
        self._last_seen[slug] = post_updated or now
        logger.info(
            "invalidation: marked %s pending_revalidation", slug
        )

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        """Write ``content`` to ``target`` atomically.

        We render to a tempfile in the same directory (same filesystem
        is required for ``os.replace`` to be atomic), fsync, then
        rename. POSIX guarantees the rename is observed as a single
        step — readers either see the old file or the new one, never
        a torn version.
        """

        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except Exception:
            # Best-effort cleanup; the OS will GC the tempfile eventually
            # but explicit removal keeps the directory tidy.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _find_page_file(self, slug: str) -> Path | None:
        """Locate the markdown file for ``slug`` across the vault.

        Pages live in one of the four type-dirs. We probe in declaration
        order; the first match wins. Returns ``None`` if none match.
        """

        for type_dir in _PAGE_TYPE_DIRS:
            candidate = self.vault_root / type_dir / f"{slug}.md"
            if candidate.exists():
                return candidate
        return None

    async def _append_log(self, record: InvalidationRecord) -> None:
        """Append one JSONL record to the audit log atomically.

        Holds an asyncio lock so concurrent ``handle_event`` tasks don't
        interleave their lines. The lock is process-local — multi-
        process deployments would need flock or a database, but we run
        single-process by design.
        """

        async with self._log_lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            line = record.model_dump_json()
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    async def _enqueue_resynth(self, slugs: list[str]) -> None:
        """Append affected slugs to the scheduler's resynth queue.

        The queue is a plain text file, one slug per line. The
        scheduler reads it on its next tick, deduplicates, kicks off a
        re-synthesis pass for each slug, and truncates the file. The
        engine is strictly append-only — coordination of "what's been
        consumed" lives on the scheduler side.

        Why a flat file: matches the rest of the engine's filesystem-
        first posture (design doc §5 'No DB'). grep-friendly for
        operators tailing the directory during an incident.
        """

        if not slugs:
            return
        async with self._resynth_lock:
            self.resynth_queue_path.parent.mkdir(parents=True, exist_ok=True)
            with self.resynth_queue_path.open("a", encoding="utf-8") as f:
                for slug in slugs:
                    f.write(slug + "\n")
