"""Read-scope tool: reconcile_docs.

Cross-source contradiction scan for a topic. Never mutates a source.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.scoped_tool import scoped_tool

from . import _docs_runtime as runtime


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic to reconcile across every configured source.",
        },
    },
    "required": ["topic"],
}


@scoped_tool("read")
def reconcile_docs(topic: str) -> dict:
    """Full cross-source comparison with flagged contradictions.

    Calls the Layer 0.4 ``LLMRouter`` if one is configured; gracefully
    falls back to string-diff-only results if the local LLM is down.
    """
    reconciler = runtime.get_reconciler()
    report = asyncio.run(reconciler.compare(topic))
    return {
        "status": "success",
        "tool": "reconcile_docs",
        "topic": topic,
        "report": report.model_dump(mode="json"),
    }


reconcile_docs.input_schema = INPUT_SCHEMA  # type: ignore[attr-defined]


__all__ = ["reconcile_docs", "INPUT_SCHEMA"]
