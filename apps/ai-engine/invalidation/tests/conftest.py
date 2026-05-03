"""Shared pytest fixtures for the invalidation test suite.

The fixtures build a temporary Obsidian-shaped vault on disk, populate
a small set of :class:`WikiPage` objects with realistic
``config_dependencies``, and return both the vault root and the page
list so tests can assert against either.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import pytest

# Resolve `from invalidation.x import ...` and `from wiki.x import ...`
# to apps/ai-engine.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))


from wiki.synthesizer import ConfigDependency, WikiPage  # noqa: E402


def _write_page(
    vault_root: Path,
    type_dir: str,
    slug: str,
    title: str,
    config_dependencies: list[ConfigDependency],
) -> Path:
    """Write a minimal valid wiki page to disk and return its path."""
    target = vault_root / type_dir / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "title": title,
        "slug": slug,
        "type": type_dir.rstrip("s") if type_dir != "concepts" else "concept",
        "freshness": "current",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        # Round-trip the dependencies through dict so YAML serializes them.
        "config_dependencies": [d.model_dump() for d in config_dependencies],
    }
    body = f"# {title}\n\nA fixture page for invalidation tests.\n"
    post = frontmatter.Post(body, **meta)
    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    return target


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """A vault root with the four standard type-dirs already created."""
    for sub in ("entities", "concepts", "incidents", "runbooks", "_meta"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def auth_replicas_dep() -> ConfigDependency:
    return ConfigDependency(
        artifact_kind="k8s",
        artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
        expected_value="3",
    )


@pytest.fixture
def auth_image_dep() -> ConfigDependency:
    return ConfigDependency(
        artifact_kind="k8s",
        artifact_id=(
            "k8s:Deployment:default/auth-service:spec.template.spec."
            "containers[0].image"
        ),
    )


@pytest.fixture
def sample_pages(
    tmp_vault: Path,
    auth_replicas_dep: ConfigDependency,
    auth_image_dep: ConfigDependency,
) -> list[WikiPage]:
    """Three pages with overlapping dependencies for index tests.

    - ``auth-service`` (entity) depends on auth replicas + auth image.
    - ``scaling-runbook`` (runbook) depends on auth replicas only.
    - ``architecture-overview`` (concept) has no dependencies.
    """
    p1 = _write_page(
        tmp_vault,
        "entities",
        "auth-service",
        "Auth Service",
        [auth_replicas_dep, auth_image_dep],
    )
    p2 = _write_page(
        tmp_vault,
        "runbooks",
        "scaling-runbook",
        "Scaling Runbook",
        [auth_replicas_dep],
    )
    p3 = _write_page(
        tmp_vault,
        "concepts",
        "architecture-overview",
        "Architecture Overview",
        [],
    )

    return [
        WikiPage.from_file(p1),
        WikiPage.from_file(p2),
        WikiPage.from_file(p3),
    ]
