"""Shared process-wide :class:`Reconciler` singleton for docs_* MCP tools.

Tests and the FastAPI app can ``set_reconciler(...)`` to inject a
pre-configured reconciler with mock sources and/or a real
:class:`~llm_router.router.LLMRouter`. Production deployments typically
bootstrap this at startup with the real sources.

If no reconciler has been set, :func:`get_reconciler` returns a default
one backed by an empty source list — the tools will simply return
empty results, which is safe behaviour for an MCP surface.
"""

from __future__ import annotations

from typing import Any

from reconciliation.reconciler import Reconciler

_reconciler: Reconciler | None = None


def set_reconciler(reconciler: Reconciler) -> None:
    """Install a process-wide reconciler used by all docs_* MCP tools."""
    global _reconciler
    _reconciler = reconciler


def set_sources(sources: list[Any], *, llm_router: Any | None = None) -> Reconciler:
    """Convenience constructor — builds + installs a reconciler."""
    global _reconciler
    _reconciler = Reconciler(sources=sources, llm_router=llm_router)
    return _reconciler


def get_reconciler() -> Reconciler:
    """Return the current reconciler, constructing an empty one if needed."""
    global _reconciler
    if _reconciler is None:
        _reconciler = Reconciler(sources=[])
    return _reconciler


def reset() -> None:
    """Test helper — clear the singleton."""
    global _reconciler
    _reconciler = None


__all__ = ["set_reconciler", "set_sources", "get_reconciler", "reset"]
