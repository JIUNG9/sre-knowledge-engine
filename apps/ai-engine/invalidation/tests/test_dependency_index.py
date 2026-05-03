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
