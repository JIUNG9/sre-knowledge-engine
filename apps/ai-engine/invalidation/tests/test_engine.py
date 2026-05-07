"""Tests for :class:`invalidation.engine.InvalidationEngine`."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import frontmatter
import pytest

from invalidation.dependency_index import DependencyIndex
from invalidation.engine import InvalidationEngine
from invalidation.models import InvalidationRecord
from state_subscription.models import StateChangeEvent
from wiki.synthesizer import WikiPage


pytestmark = pytest.mark.asyncio


def _read_freshness(page_path: Path) -> str:
    return frontmatter.load(str(page_path))["freshness"]


def _read_log(log_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


async def test_handle_event_marks_dependent_pages_pending(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    event = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        old_value="3",
        new_value="5",
        source="k8s://default/auth-service",
    )
    record = await engine.handle_event(event)

    assert record.affected_slugs == ["auth-service", "scaling-runbook"]
    assert record.reason == "value_change"
    assert record.shadow_mode is False

    assert _read_freshness(tmp_vault / "entities" / "auth-service.md") == (
        "pending_revalidation"
    )
    assert _read_freshness(tmp_vault / "runbooks" / "scaling-runbook.md") == (
        "pending_revalidation"
    )
    # The concept page is unaffected — it had no dependencies.
    assert _read_freshness(tmp_vault / "concepts" / "architecture-overview.md") == (
        "current"
    )


async def test_handle_event_records_first_observation_reason(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    # First observation: old_value=None.
    event = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        old_value=None,
        new_value="3",
        source="k8s://default/auth-service",
    )
    record = await engine.handle_event(event)
    assert record.reason == "first_observation"


async def test_handle_event_no_dependents_writes_log_no_mutation(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """Unknown artifact_id: no pages mutated, but the audit record is still
    written so the consumer's observation is recorded."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    event = StateChangeEvent(
        artifact_kind="argocd",
        artifact_id="argocd:app:nope:targetRevision",
        old_value="abc",
        new_value="def",
        source="argocd://nope",
    )
    record = await engine.handle_event(event)

    assert record.affected_slugs == []

    # Every page still 'current'.
    for path in (
        tmp_vault / "entities" / "auth-service.md",
        tmp_vault / "runbooks" / "scaling-runbook.md",
        tmp_vault / "concepts" / "architecture-overview.md",
    ):
        assert _read_freshness(path) == "current"

    # Log entry written.
    log = _read_log(engine.log_path)
    assert len(log) == 1
    assert log[0]["affected_slugs"] == []
    assert log[0]["artifact_id"] == "argocd:app:nope:targetRevision"


async def test_shadow_mode_logs_without_mutating(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(
        vault_root=tmp_vault, index=index, shadow_mode=True
    )

    event = StateChangeEvent(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        old_value="3",
        new_value="5",
        source="k8s://default/auth-service",
    )
    record = await engine.handle_event(event)

    assert record.shadow_mode is True
    assert record.affected_slugs == ["auth-service", "scaling-runbook"]
    # Pages unchanged despite a non-empty affected_slugs list.
    assert _read_freshness(tmp_vault / "entities" / "auth-service.md") == "current"
    assert _read_freshness(tmp_vault / "runbooks" / "scaling-runbook.md") == "current"

    log = _read_log(engine.log_path)
    assert len(log) == 1
    assert log[0]["shadow_mode"] is True


async def test_consume_drains_async_iterator(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    async def event_stream() -> AsyncIterator[StateChangeEvent]:
        yield StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
        yield StateChangeEvent(
            artifact_kind="k8s",
            artifact_id=(
                "k8s:Deployment:default/auth-service:spec.template.spec."
                "containers[0].image"
            ),
            old_value="acme-corp/auth:1.0",
            new_value="acme-corp/auth:1.1",
            source="k8s://default/auth-service",
        )

    await engine.consume(event_stream())

    assert _read_freshness(tmp_vault / "entities" / "auth-service.md") == (
        "pending_revalidation"
    )
    log = _read_log(engine.log_path)
    assert len(log) == 2
    assert {entry["artifact_id"] for entry in log} == {
        "k8s:Deployment:default/auth-service:spec.replicas",
        "k8s:Deployment:default/auth-service:spec.template.spec.containers[0].image",
    }


async def test_consume_swallows_per_event_exceptions(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bad event must not abort the loop; subsequent events still process."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    seen: list[str] = []
    real_handle = engine.handle_event

    async def flaky_handle(event: StateChangeEvent) -> InvalidationRecord:
        seen.append(event.artifact_id)
        if event.artifact_id == "boom":
            raise RuntimeError("synthetic failure")
        return await real_handle(event)

    monkeypatch.setattr(engine, "handle_event", flaky_handle)

    async def stream() -> AsyncIterator[StateChangeEvent]:
        yield StateChangeEvent(
            artifact_kind="cloud",
            artifact_id="boom",
            new_value="x",
            source="test",
        )
        yield StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )

    await engine.consume(stream())

    assert "boom" in seen
    assert _read_freshness(tmp_vault / "entities" / "auth-service.md") == (
        "pending_revalidation"
    )


async def test_log_is_append_only_jsonl(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    # Three events, three lines.
    for idx in range(3):
        await engine.handle_event(
            StateChangeEvent(
                artifact_kind="k8s",
                artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
                old_value=str(idx),
                new_value=str(idx + 1),
                source="k8s://default/auth-service",
            )
        )

    log_text = engine.log_path.read_text(encoding="utf-8")
    lines = [line for line in log_text.splitlines() if line.strip()]
    assert len(lines) == 3
    # Each line is a valid JSON object.
    for line in lines:
        record = json.loads(line)
        assert record["artifact_id"].endswith("spec.replicas")
        assert isinstance(record["affected_slugs"], list)


async def test_missing_page_file_is_logged_not_raised(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """Index points at a slug whose page was deleted out from under us —
    we warn and continue, the audit log still records the event."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    # Delete one of the dependent pages on disk.
    (tmp_vault / "runbooks" / "scaling-runbook.md").unlink()

    record = await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )
    # auth-service still on disk, scaling-runbook gone — both still in
    # affected_slugs because the index says so.
    assert record.affected_slugs == ["auth-service", "scaling-runbook"]
    assert _read_freshness(tmp_vault / "entities" / "auth-service.md") == (
        "pending_revalidation"
    )


async def test_write_is_atomic_no_tempfiles_left_behind(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """After a successful invalidation rewrite, the page directory must
    contain only the original ``.md`` files — no leftover tempfiles
    from the atomic-write path."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )

    entities = list((tmp_vault / "entities").iterdir())
    runbooks = list((tmp_vault / "runbooks").iterdir())
    # Exactly one .md per dir, nothing prefixed with "." or ending ".tmp".
    assert [p.name for p in entities] == ["auth-service.md"]
    assert [p.name for p in runbooks] == ["scaling-runbook.md"]


async def test_resynth_queue_appended_with_affected_slugs(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """After handle_event, the resynth queue file contains exactly the
    slugs the record marked. Two events on the same dependents append
    twice — the scheduler is expected to dedupe."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    artifact = "k8s:Deployment:default/auth-service:spec.replicas"
    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id=artifact,
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )

    queue_path = tmp_vault / "_meta" / "resynth-queue.txt"
    lines = queue_path.read_text(encoding="utf-8").splitlines()
    assert sorted(lines) == ["auth-service", "scaling-runbook"]

    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id=artifact,
            old_value="5",
            new_value="6",
            source="k8s://default/auth-service",
        )
    )
    lines2 = queue_path.read_text(encoding="utf-8").splitlines()
    # Second event appends — dedup is the scheduler's job, not ours.
    assert len(lines2) == 4


async def test_resynth_queue_skipped_in_shadow_mode(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """Shadow mode means the engine logs but never mutates. The resynth
    queue is a mutation — it must stay empty under the shadow flag."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(
        vault_root=tmp_vault, index=index, shadow_mode=True
    )

    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )

    queue_path = tmp_vault / "_meta" / "resynth-queue.txt"
    assert not queue_path.exists()


async def test_fanout_cap_truncates_and_flags_record(
    tmp_vault: Path,
) -> None:
    """An artifact that 50 pages depend on, with a fanout_cap of 5,
    should produce: 5 marked pages, truncated=True, total_dependents=50."""
    import frontmatter as fm
    from datetime import datetime, timezone

    artifact = "k8s:Deployment:default/popular-svc:spec.replicas"
    pages: list[WikiPage] = []
    for i in range(50):
        slug = f"dep-page-{i:03d}"
        path = tmp_vault / "entities" / f"{slug}.md"
        meta = {
            "title": slug,
            "slug": slug,
            "type": "entity",
            "freshness": "current",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "config_dependencies": [
                {
                    "artifact_kind": "k8s",
                    "artifact_id": artifact,
                    "expected_value": "3",
                    "invalidate_on_change": True,
                }
            ],
        }
        path.write_text(
            fm.dumps(fm.Post(f"# {slug}\n", **meta)), encoding="utf-8"
        )
        pages.append(WikiPage.from_file(path))

    index = DependencyIndex()
    await index.rebuild(pages)
    engine = InvalidationEngine(
        vault_root=tmp_vault, index=index, fanout_cap=5
    )

    record = await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id=artifact,
            old_value="3",
            new_value="9",
            source="k8s://default/popular-svc",
        )
    )

    assert record.truncated is True
    assert record.total_dependents == 50
    assert len(record.affected_slugs) == 5
    # Sorted prefix is deterministic — first 5 lexicographically.
    assert record.affected_slugs == [f"dep-page-{i:03d}" for i in range(5)]
    # Only the 5 that fit the cap should be marked; the other 45 stay
    # `current` until reconciliation sweeps them.
    assert (
        _read_freshness(tmp_vault / "entities" / "dep-page-004.md")
        == "pending_revalidation"
    )
    assert (
        _read_freshness(tmp_vault / "entities" / "dep-page-005.md")
        == "current"
    )


async def test_batching_collapses_flapping_events(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """A ConfigMap flaps six times in under 100ms. With batching, the
    engine writes the audit log once for that artifact (last event
    wins), not six times. Reconciliation handles the rare lost
    intermediate value (design §5)."""
    import asyncio

    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    artifact = "k8s:Deployment:default/auth-service:spec.replicas"

    async def stream() -> AsyncIterator[StateChangeEvent]:
        # Six events in a tight burst, then we close the stream.
        for new_value in ("4", "5", "4", "6", "5", "7"):
            yield StateChangeEvent(
                artifact_kind="k8s",
                artifact_id=artifact,
                old_value="3",
                new_value=new_value,
                source="k8s://default/auth-service",
            )
            # Tiny gap so we don't blow past the batch window in one
            # event-loop tick — still well under the 100ms deadline.
            await asyncio.sleep(0.005)

    await engine.consume_with_batching(stream(), batch_window=0.1)

    log_records = _read_log(
        tmp_vault / "_meta" / "invalidation-log.jsonl"
    )
    flap_records = [
        r for r in log_records if r["artifact_id"] == artifact
    ]
    # Exactly one record for the flap — the last event's new_value
    # wins and the intermediate flapping is collapsed.
    assert len(flap_records) == 1
    assert flap_records[0]["new_value"] == "7"


async def test_concurrent_edit_skips_rewrite(
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """A human edits the page after the engine first marked it. A
    second event with a stale last-seen must NOT clobber the human's
    edit — concurrent-edit conflict, operator wins (design §7)."""
    from datetime import datetime, timezone

    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = InvalidationEngine(vault_root=tmp_vault, index=index)

    page_path = tmp_vault / "entities" / "auth-service.md"
    artifact = "k8s:Deployment:default/auth-service:spec.replicas"

    # Tick 1: engine marks the page. last_seen is set.
    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id=artifact,
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )
    assert _read_freshness(page_path) == "pending_revalidation"

    # Human edits the page out-of-band: marks it `current` again with a
    # last_updated timestamp newer than what the engine has on record.
    post = frontmatter.load(str(page_path))
    post["freshness"] = "current"
    post["last_updated"] = datetime(
        2099, 1, 1, tzinfo=timezone.utc
    ).isoformat()
    page_path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # Tick 2: another event arrives. Engine should detect the human
    # edit and skip the rewrite — page stays `current`.
    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id=artifact,
            old_value="5",
            new_value="6",
            source="k8s://default/auth-service",
        )
    )
    assert _read_freshness(page_path) == "current"
