"""Pydantic types shared across the reconciliation engine.

All types are intentionally pure data — they contain no I/O. That keeps
them cheap to serialise into MCP tool responses and easy to synthesise
in tests without touching real sources.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Primary doc model
# --------------------------------------------------------------------------- #


SourceName = Literal[
    "obsidian",
    "confluence",
    "github_wiki",
    "slack_pin",
]


class Doc(BaseModel):
    """A single document fetched from one of the registered sources.

    The ``id`` is source-local (e.g. a Confluence page id, an Obsidian
    file path) — uniqueness is only required within one source. The
    ``global_id`` convenience property combines ``source + id``.
    """

    id: str
    source: SourceName
    title: str
    body: str = ""
    url: str | None = None
    last_modified: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def global_id(self) -> str:
        return f"{self.source}:{self.id}"


class DocRef(BaseModel):
    """A lightweight pointer to a Doc, used for ranked search results.

    The reconciler returns these rather than full ``Doc`` objects so
    large bodies don't travel through the MCP channel unless a caller
    explicitly asks for them.
    """

    id: str
    source: SourceName
    title: str
    url: str | None = None
    last_modified: datetime | None = None
    freshness_score: float = 0.0  # 0.0 = totally stale, 1.0 = freshest
    snippet: str = ""  # first few lines of the body


# --------------------------------------------------------------------------- #
# Contradiction report
# --------------------------------------------------------------------------- #


SeverityT = Literal["critical", "warning", "info"]
CategoryT = Literal[
    "version_mismatch",
    "procedure_conflict",
    "coverage_gap",
    "factual_contradiction",
]


class Contradiction(BaseModel):
    """A single pair of conflicting claims between two docs."""

    doc_a: str  # global_id
    doc_b: str  # global_id
    claim_a: str
    claim_b: str
    severity: SeverityT = "warning"
    category: CategoryT = "factual_contradiction"
    explanation: str = ""


class ReconciliationReport(BaseModel):
    """Output of a cross-source reconciliation pass for one topic."""

    topic: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    docs: list[DocRef] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    sources_queried: list[str] = Field(default_factory=list)
    llm_backend: str | None = None  # "claude" | "ollama" | None (fallback)
    llm_available: bool = True
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Staleness
# --------------------------------------------------------------------------- #


class StalenessScore(BaseModel):
    """Structured explanation of *why* a doc is stale."""

    doc_id: str
    source: SourceName
    score: float  # 0.0 = fresh, 1.0 = extremely stale
    age_days: int | None = None
    reasons: list[str] = Field(default_factory=list)
    stale_indicators: list[str] = Field(default_factory=list)
    decommissioned_refs: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Link report
# --------------------------------------------------------------------------- #


LinkStatus = Literal["ok", "broken", "timeout", "skipped_robots", "unchecked"]


class LinkCheckResult(BaseModel):
    """Result of a single link probe."""

    url: str
    status: LinkStatus
    http_status: int | None = None
    reason: str | None = None


class LinkReport(BaseModel):
    """Full link-check output for one document."""

    doc_id: str
    source: SourceName
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checked: list[LinkCheckResult] = Field(default_factory=list)
    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)

    @property
    def broken_count(self) -> int:
        return sum(1 for c in self.checked if c.status in ("broken", "timeout"))


__all__ = [
    "Doc",
    "DocRef",
    "SourceName",
    "Contradiction",
    "ReconciliationReport",
    "SeverityT",
    "CategoryT",
    "StalenessScore",
    "LinkStatus",
    "LinkCheckResult",
    "LinkReport",
]
