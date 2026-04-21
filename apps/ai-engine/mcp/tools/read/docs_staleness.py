"""Read-scope tool: detect_stale_docs.

Sweeps a single source for docs past a staleness threshold and
returns structured reasons.
"""

from __future__ import annotations

from typing import Any

from mcp.scoped_tool import scoped_tool
from reconciliation.drift import score_staleness

from . import _docs_runtime as runtime


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source": {
            "type": "string",
            "enum": ["obsidian", "confluence", "github_wiki", "slack_pin"],
            "description": "Which source to sweep.",
        },
        "threshold_days": {
            "type": "integer",
            "description": (
                "Age threshold in days. Docs older than this — or with "
                "non-age staleness signals above the internal score cutoff — "
                "are returned."
            ),
            "default": 180,
            "minimum": 0,
        },
    },
    "required": ["source"],
}


@scoped_tool("read")
def detect_stale_docs(source: str, threshold_days: int = 180) -> dict:
    """Return docs from ``source`` that exceed the staleness threshold."""
    reconciler = runtime.get_reconciler()
    src = next((s for s in reconciler.sources if s.name == source), None)
    if src is None:
        return {
            "status": "error",
            "tool": "detect_stale_docs",
            "error": f"source {source!r} is not configured",
            "available_sources": [s.name for s in reconciler.sources],
        }

    stale: list[dict[str, Any]] = []
    for doc_id in src.list():
        doc = src.fetch(doc_id)
        if doc is None:
            continue
        score = score_staleness(doc)
        # Threshold trips on either raw age OR a combined score >= 0.5
        age_trip = score.age_days is not None and score.age_days >= threshold_days
        score_trip = score.score >= 0.5
        if age_trip or score_trip:
            stale.append(
                {
                    "doc_id": doc.id,
                    "title": doc.title,
                    "url": doc.url,
                    "staleness": score.model_dump(mode="json"),
                }
            )
    stale.sort(key=lambda d: -d["staleness"]["score"])
    return {
        "status": "success",
        "tool": "detect_stale_docs",
        "source": source,
        "threshold_days": threshold_days,
        "count": len(stale),
        "stale_docs": stale,
    }


detect_stale_docs.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["detect_stale_docs", "INPUT_SCHEMA"]
