"""Layer 1.6 invalidation engine.

Consumes :class:`state_subscription.models.StateChangeEvent` values,
fans them out to dependent wiki pages via a
:class:`DependencyIndex`, and marks affected pages
``freshness=pending_revalidation`` so the scheduler picks them up for
re-synthesis.

Optimistic imports: a missing optional submodule (e.g. ``frontmatter``
not installed in a slim environment) leaves the symbol bound to None
and the rest of the package importable. The router or service that
needs the engine reports "feature unavailable" rather than crashing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "InvalidationEngine",
    "DependencyIndex",
    "InvalidationRecord",
    "InvalidationReason",
]

if TYPE_CHECKING:
    from .dependency_index import DependencyIndex  # noqa: F401
    from .engine import InvalidationEngine  # noqa: F401
    from .models import InvalidationReason, InvalidationRecord  # noqa: F401


try:
    from .models import InvalidationReason, InvalidationRecord  # type: ignore[assignment]
except Exception:  # pragma: no cover
    InvalidationRecord = None  # type: ignore[assignment]
    InvalidationReason = None  # type: ignore[assignment]

try:
    from .dependency_index import DependencyIndex  # type: ignore[assignment]
except Exception:  # pragma: no cover
    DependencyIndex = None  # type: ignore[assignment]

try:
    from .engine import InvalidationEngine  # type: ignore[assignment]
except Exception:  # pragma: no cover
    InvalidationEngine = None  # type: ignore[assignment]
