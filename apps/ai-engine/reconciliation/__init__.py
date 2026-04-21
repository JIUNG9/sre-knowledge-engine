"""Document reconciliation engine — Layer 5.

Cross-source document search, contradiction detection, and staleness
scoring for scattered documentation (Obsidian, Confluence, GitHub wikis,
Slack pins). Surfaced to Claude via four read-only MCP tools:

- ``find_docs`` — ranked cross-source search.
- ``reconcile_docs`` — full contradiction report for a topic.
- ``detect_stale_docs`` — per-source freshness sweep.
- ``check_doc_links`` — internal + external link validator.

Every data source subclasses :class:`~reconciliation.sources.DocSource`,
so adding a new backend is a 30-line exercise that requires no changes
to the engine. All LLM calls go through the Layer 0.4 ``LLMRouter`` so
sensitive doc bodies route to Ollama by default.
"""

from __future__ import annotations

from .drift import StalenessScore, score_staleness
from .models import Contradiction, Doc, DocRef, LinkReport, ReconciliationReport
from .reconciler import Reconciler
from .sources import (
    ConfluenceSource,
    DocSource,
    GitHubWikiSource,
    ObsidianSource,
    SlackPinSource,
)

__all__ = [
    "Contradiction",
    "Doc",
    "DocRef",
    "DocSource",
    "ConfluenceSource",
    "GitHubWikiSource",
    "ObsidianSource",
    "SlackPinSource",
    "LinkReport",
    "Reconciler",
    "ReconciliationReport",
    "StalenessScore",
    "score_staleness",
]
