"""Tests for :class:`invalidation.dependency_index.DependencyIndex`."""

from __future__ import annotations

import pytest

from invalidation.dependency_index import DependencyIndex
from wiki.synthesizer import ConfigDependency, WikiPage


pytestmark = pytest.mark.asyncio


async def test_rebuild_populates_reverse_index(sample_pages: list[WikiPage]) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)

    # Two pages depend on auth-service replicas.
    replicas_id = "k8s:Deployment:default/auth-service:spec.replicas"
    slugs = await index.lookup(replicas_id)
    assert slugs == {"auth-service", "scaling-runbook"}

    # One page depends on the auth-service container image.
    image_id = (
        "k8s:Deployment:default/auth-service:spec.template.spec.containers[0].image"
    )
    image_slugs = await index.lookup(image_id)
    assert image_slugs == {"auth-service"}

    # The concept page contributes nothing.
    snapshot = await index.snapshot()
    for slugs in snapshot.values():
        assert "architecture-overview" not in slugs


async def test_lookup_returns_empty_set_for_unknown_artifact() -> None:
    index = DependencyIndex()
    slugs = await index.lookup("k8s:Deployment:default/nope:spec.replicas")
    assert slugs == set()


async def test_lookup_returns_copy_not_reference(
    sample_pages: list[WikiPage],
) -> None:
    """Mutating the returned set must not corrupt the index."""
    index = DependencyIndex()
    await index.rebuild(sample_pages)

    replicas_id = "k8s:Deployment:default/auth-service:spec.replicas"
    slugs = await index.lookup(replicas_id)
    slugs.add("imposter")

    fresh = await index.lookup(replicas_id)
    assert "imposter" not in fresh


async def test_upsert_page_replaces_existing_dependencies(
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)

    # Reduce the auth-service page's dependencies to image only.
    auth_page = next(p for p in sample_pages if p.slug == "auth-service")
    auth_page.config_dependencies = [
        ConfigDependency(
            artifact_kind="k8s",
            artifact_id=(
                "k8s:Deployment:default/auth-service:spec.template.spec."
                "containers[0].image"
            ),
        )
    ]
    await index.upsert_page(auth_page)

    replicas_id = "k8s:Deployment:default/auth-service:spec.replicas"
    after = await index.lookup(replicas_id)
    # Only scaling-runbook should still claim this artifact.
    assert after == {"scaling-runbook"}


async def test_upsert_page_adds_new_dependency(
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)

    new_artifact = "terraform:rds.tf:aurora_postgres_version"
    page = sample_pages[0]
    page.config_dependencies = [
        *page.config_dependencies,
        ConfigDependency(artifact_kind="terraform", artifact_id=new_artifact),
    ]
    await index.upsert_page(page)

    slugs = await index.lookup(new_artifact)
    assert slugs == {page.slug}


async def test_remove_page_drops_slug_from_all_buckets(
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)

    await index.remove_page("auth-service")

    snapshot = await index.snapshot()
    for slugs in snapshot.values():
        assert "auth-service" not in slugs

    # The replicas bucket still has scaling-runbook.
    replicas_id = "k8s:Deployment:default/auth-service:spec.replicas"
    assert await index.lookup(replicas_id) == {"scaling-runbook"}


async def test_rebuild_overwrites_previous_state(
    sample_pages: list[WikiPage],
) -> None:
    index = DependencyIndex()
    await index.rebuild(sample_pages)

    # Now rebuild with a single empty page — every bucket must clear.
    just_one = [
        WikiPage(
            title="Empty",
            type="concept",
            slug="empty",
            path=sample_pages[0].path.parent / "empty.md",
            config_dependencies=[],
        )
    ]
    await index.rebuild(just_one)
    snapshot = await index.snapshot()
    assert snapshot == {}


async def test_from_vault_walks_page_dirs(
    tmp_vault, sample_pages: list[WikiPage]
) -> None:
    """The bootstrap loader walks the four standard page dirs and builds
    the same index a hand-fed rebuild would. sample_pages already wrote
    the pages to disk via the conftest fixture, so we just call the
    loader and assert equivalence."""
    index = await DependencyIndex.from_vault(tmp_vault)

    replicas_id = "k8s:Deployment:default/auth-service:spec.replicas"
    assert await index.lookup(replicas_id) == {
        "auth-service", "scaling-runbook"
    }


async def test_from_vault_returns_empty_when_path_missing(tmp_path) -> None:
    """A missing vault_root must not crash startup — return an empty
    index and log a warning. The engine with an empty index is still
    safe to run; it just no-ops on every event."""
    missing = tmp_path / "does-not-exist"
    index = await DependencyIndex.from_vault(missing)
    assert await index.snapshot() == {}


async def test_from_vault_skips_corrupt_pages(tmp_vault) -> None:
    """A single corrupt frontmatter file must not block startup. The
    loader logs and skips it, returning an index built from the
    parseable peers."""
    # One valid page.
    valid = tmp_vault / "entities" / "valid.md"
    valid.write_text(
        "---\n"
        "title: Valid\nslug: valid\ntype: entity\nfreshness: current\n"
        "config_dependencies:\n"
        "- {artifact_kind: k8s, artifact_id: 'k8s:Deployment:default/x:spec.replicas'}\n"
        "---\n# Valid\n",
        encoding="utf-8",
    )
    # One garbage file the parser can't handle.
    garbage = tmp_vault / "entities" / "garbage.md"
    garbage.write_text("not yaml frontmatter at all\n%%%\n", encoding="utf-8")

    index = await DependencyIndex.from_vault(tmp_vault)
    snapshot = await index.snapshot()
    # Valid page got indexed; garbage was skipped.
    assert "k8s:Deployment:default/x:spec.replicas" in snapshot
