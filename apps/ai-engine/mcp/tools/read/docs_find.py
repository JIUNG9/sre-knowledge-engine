"""Read-scope tool: find_docs.

Cross-source document search. Returns a freshness-ranked list of
:class:`~reconciliation.models.DocRef` pointers. Read-only — never
mutates a source.
"""

from __future__ import annotations

from typing import Any

from mcp.scoped_tool import scoped_tool

from . import _docs_runtime as runtime


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Substring/keyword to search across every configured source.",
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["obsidian", "confluence", "github_wiki", "slack_pin"],
            },
            "description": "Optional list of source names to restrict the search.",
        },
    },
    "required": ["topic"],
}


@scoped_tool("read")
def find_docs(topic: str, sources: list[str] | None = None) -> dict:
    """Find documents matching a topic across every configured source.

    Returns a dict with a ``docs`` key containing ranked
    :class:`DocRef` entries (freshest first).
    """
    reconciler = runtime.get_reconciler()
    refs = reconciler.find(topic, sources=sources)
    return {
        "status": "success",
        "tool": "find_docs",
        "topic": topic,
        "sources": sources or [s.name for s in reconciler.sources],
        "count": len(refs),
        "docs": [ref.model_dump(mode="json") for ref in refs],
    }


find_docs.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["find_docs", "INPUT_SCHEMA"]
