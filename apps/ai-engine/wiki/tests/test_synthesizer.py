"""Tests for the WikiPage schema migration (Layer 1.5 / 1.6 additions).

The migration adds two optional fields (`config_dependencies`, `scope`)
and one new freshness state (`pending_revalidation`). All changes must
be backward-compatible: pages written before the migration still load,
and the new fields round-trip cleanly through YAML frontmatter.
"""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import pytest

# Ensure ``from wiki.synthesizer import ...`` resolves to apps/ai-engine when
# the suite is run via an explicit path (this dir is not in pyproject's
# `testpaths`, so pyproject's `pythonpath = ["."]` doesn't always kick in).
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))

from wiki.synthesizer import (  # noqa: E402 - sys.path tweak above
    ClaimScope,
    ConfigDependency,
    WikiPage,
)


# --- Backward compatibility -------------------------------------------------- #


def test_wikipage_loads_legacy_frontmatter_without_new_fields(tmp_path: Path) -> None:
    """A page written before Layer 1.5 must still load and serialize."""
    legacy_md = tmp_path / "old-page.md"
    legacy_md.write_text(
        textwrap.dedent(
            """
            ---
            title: Auth Service
            type: entity
            slug: auth-service
            last_updated: 2026-01-15T10:00:00
            sources: ["confluence:DB-Architecture"]
            freshness: current
            ---
            Body text.
            """
        ).strip(),
        encoding="utf-8",
    )

    page = WikiPage.from_file(legacy_md)
    assert page.config_dependencies == []
    assert page.scope is None
    assert page.freshness == "current"
    assert page.title == "Auth Service"
    assert page.sources == ["confluence:DB-Architecture"]

    # Round-tripping a legacy page must not crash even though it now has
    # to emit the new fields (as empty list / null).
    rendered = page.to_markdown()
    parsed = frontmatter.loads(rendered)
    assert parsed.metadata["config_dependencies"] == []
    assert parsed.metadata["scope"] is None


# --- Round-trip of new fields ----------------------------------------------- #


def test_wikipage_roundtrips_config_dependencies() -> None:
    """Set config_dependencies, serialize, parse back — fields preserved."""
    page = WikiPage(
        title="Auth Service",
        type="entity",
        slug="auth-service",
        path=Path("entities/auth-service.md"),
        frontmatter={},
        body="...",
        last_updated=datetime(2026, 4, 26, tzinfo=timezone.utc),
        sources=[],
        freshness="current",
        config_dependencies=[
            ConfigDependency(
                artifact_kind="k8s",
                artifact_id="k8s:Deployment:auth-service:spec.replicas",
                expected_value="3",
            ),
        ],
    )
    md = page.to_markdown()
    # Re-parse via the frontmatter library directly so we're testing the YAML
    # round-trip, not just our own from_file path.
    parsed = frontmatter.loads(md)
    deps = parsed.metadata["config_dependencies"]
    assert isinstance(deps, list) and len(deps) == 1
    assert deps[0]["artifact_kind"] == "k8s"
    assert deps[0]["artifact_id"] == "k8s:Deployment:auth-service:spec.replicas"
    assert deps[0]["expected_value"] == "3"
    assert deps[0]["invalidate_on_change"] is True


def test_wikipage_roundtrips_through_disk(tmp_path: Path) -> None:
    """Nested ConfigDependency / ClaimScope survive disk write + from_file."""
    page = WikiPage(
        title="Auth Service",
        type="entity",
        slug="auth-service",
        path=tmp_path / "entities" / "auth-service.md",
        frontmatter={},
        body="Body.",
        last_updated=datetime(2026, 4, 26, tzinfo=timezone.utc),
        sources=["confluence:Auth"],
        freshness="pending_revalidation",
        config_dependencies=[
            ConfigDependency(
                artifact_kind="terraform",
                artifact_id="terraform:rds.tf:aurora_postgres_version",
                expected_value="16.2",
                invalidate_on_change=True,
            ),
            ConfigDependency(
                artifact_kind="argocd",
                artifact_id="argocd:app:auth-service:targetRevision",
            ),
        ],
        scope=ClaimScope(
            specific_to={"service": "auth-service"},
            generalizes_to="with_conditions",
            generalizes_conditions="If running PG >= 16",
            trust_in_scope=0.92,
            trust_out_of_scope=0.15,
        ),
    )
    saved_path = page.save(tmp_path)
    reloaded = WikiPage.from_file(saved_path)

    assert reloaded.freshness == "pending_revalidation"
    assert len(reloaded.config_dependencies) == 2
    assert reloaded.config_dependencies[0].artifact_kind == "terraform"
    assert reloaded.config_dependencies[0].expected_value == "16.2"
    # Default value for the second dep was None and should round-trip.
    assert reloaded.config_dependencies[1].expected_value is None
    assert reloaded.config_dependencies[1].invalidate_on_change is True

    assert reloaded.scope is not None
    assert reloaded.scope.specific_to == {"service": "auth-service"}
    assert reloaded.scope.generalizes_to == "with_conditions"
    assert reloaded.scope.generalizes_conditions == "If running PG >= 16"
    assert reloaded.scope.trust_in_scope == 0.92


# --- ClaimScope behaviour --------------------------------------------------- #


def test_claim_scope_matches_and_trust() -> None:
    scope = ClaimScope(
        specific_to={"service": "auth-service", "error_signature": "OOMKilled"},
        generalizes_to="no",
        trust_in_scope=0.95,
        trust_out_of_scope=0.10,
    )
    assert scope.matches({"service": "auth-service", "error_signature": "OOMKilled"})
    assert not scope.matches({"service": "auth-service"})  # missing key
    assert not scope.matches(
        {"service": "billing-service", "error_signature": "OOMKilled"}
    )

    assert (
        scope.trust_for(
            {"service": "auth-service", "error_signature": "OOMKilled"}
        )
        == 0.95
    )
    assert (
        scope.trust_for(
            {"service": "billing-service", "error_signature": "OOMKilled"}
        )
        == 0.10
    )


def test_claim_scope_generalizes_caps_trust() -> None:
    """`generalizes_to` controls the out-of-scope trust ceiling."""
    yes_scope = ClaimScope(
        specific_to={"service": "auth"},
        generalizes_to="yes",
        trust_in_scope=0.99,
    )
    # Out of scope but generalizes — capped at 0.85 even though in_scope is 0.99.
    assert yes_scope.trust_for({"service": "billing"}) == 0.85

    cond_scope = ClaimScope(
        specific_to={"service": "auth"},
        generalizes_to="with_conditions",
        trust_in_scope=0.99,
    )
    assert cond_scope.trust_for({"service": "billing"}) == 0.50


def test_claim_scope_rejects_out_of_range_trust() -> None:
    """Pydantic field constraints (ge=0, le=1) must hold."""
    with pytest.raises(Exception):  # pydantic.ValidationError
        ClaimScope(specific_to={}, trust_in_scope=1.5)
    with pytest.raises(Exception):
        ClaimScope(specific_to={}, trust_out_of_scope=-0.1)


# --- Freshness migration ---------------------------------------------------- #


def test_pending_revalidation_freshness_state() -> None:
    page = WikiPage(
        title="X",
        type="entity",
        slug="x",
        path=Path("entities/x.md"),
        frontmatter={},
        body="",
        last_updated=datetime.now(timezone.utc),
        sources=[],
        freshness="pending_revalidation",
    )
    assert page.freshness == "pending_revalidation"


def test_legacy_freshness_states_still_accepted() -> None:
    """Existing freshness states are unchanged by the migration."""
    for state in ("current", "stale", "archived", "needs_review"):
        page = WikiPage(
            title="X",
            type="entity",
            slug="x",
            path=Path("entities/x.md"),
            frontmatter={},
            body="",
            last_updated=datetime.now(timezone.utc),
            sources=[],
            freshness=state,  # type: ignore[arg-type]
        )
        assert page.freshness == state


def test_pending_revalidation_roundtrips_via_from_file(tmp_path: Path) -> None:
    """The new freshness state must survive disk persistence."""
    md = tmp_path / "page.md"
    md.write_text(
        textwrap.dedent(
            """
            ---
            title: Auth
            type: entity
            slug: auth
            last_updated: 2026-04-26T00:00:00+00:00
            sources: []
            freshness: pending_revalidation
            ---
            body
            """
        ).strip(),
        encoding="utf-8",
    )
    page = WikiPage.from_file(md)
    assert page.freshness == "pending_revalidation"
