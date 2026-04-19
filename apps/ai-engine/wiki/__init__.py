"""Aegis LLM Wiki Engine.

Canonical import surface for the wiki package. Parallel agents populate the
individual modules; this file consolidates the exports so the FastAPI router
and orchestrator have a stable import path even while the package is still
under construction. Missing submodules degrade gracefully — the names remain
unbound and the router reports 503 rather than crashing at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "WikiEngine",
    "WikiEngineConfig",
    "Ingester",
    "Source",
    "SourceType",
    "Synthesizer",
    "WikiPage",
    "SynthesisDecision",
    "ContradictionDetector",
    "Contradiction",
    "ContradictionReport",
    "StalenessLinter",
    "StalenessReport",
    "StalenessRule",
    "DEFAULT_RULES",
    "ConfluenceSync",
    "ConfluenceConfig",
    "ConfluenceSyncResult",
    "SignozSync",
    "SignozConfig",
    "SignozSyncResult",
    "Publisher",
    "PublisherConfig",
    "PublishResult",
]

# Static type-checker sees the full surface unconditionally.
if TYPE_CHECKING:
    from wiki.confluence_sync import (  # noqa: F401
        ConfluenceConfig,
        ConfluenceSync,
        ConfluenceSyncResult,
    )
    from wiki.contradiction import (  # noqa: F401
        Contradiction,
        ContradictionDetector,
        ContradictionReport,
    )
    from wiki.engine import WikiEngine, WikiEngineConfig  # noqa: F401
    from wiki.ingester import Ingester, Source, SourceType  # noqa: F401
    from wiki.publisher import (  # noqa: F401
        PublishResult,
        Publisher,
        PublisherConfig,
    )
    from wiki.signoz_sync import (  # noqa: F401
        SignozConfig,
        SignozSync,
        SignozSyncResult,
    )
    from wiki.staleness import (  # noqa: F401
        DEFAULT_RULES,
        StalenessLinter,
        StalenessReport,
        StalenessRule,
    )
    from wiki.synthesizer import (  # noqa: F401
        SynthesisDecision,
        Synthesizer,
        WikiPage,
    )


# Runtime imports tolerate partially-populated packages so the ai-engine
# can still boot while parallel agents complete work.
try:
    from wiki.engine import WikiEngine, WikiEngineConfig  # type: ignore[assignment]
except Exception:  # pragma: no cover
    WikiEngine = None  # type: ignore[assignment]
    WikiEngineConfig = None  # type: ignore[assignment]

try:
    from wiki.ingester import Ingester, Source, SourceType  # type: ignore[assignment]
except Exception:  # pragma: no cover
    Ingester = None  # type: ignore[assignment]
    Source = None  # type: ignore[assignment]
    SourceType = None  # type: ignore[assignment]

try:
    from wiki.synthesizer import (  # type: ignore[assignment]
        SynthesisDecision,
        Synthesizer,
        WikiPage,
    )
except Exception:  # pragma: no cover
    Synthesizer = None  # type: ignore[assignment]
    WikiPage = None  # type: ignore[assignment]
    SynthesisDecision = None  # type: ignore[assignment]

try:
    from wiki.contradiction import (  # type: ignore[assignment]
        Contradiction,
        ContradictionDetector,
        ContradictionReport,
    )
except Exception:  # pragma: no cover
    ContradictionDetector = None  # type: ignore[assignment]
    Contradiction = None  # type: ignore[assignment]
    ContradictionReport = None  # type: ignore[assignment]

try:
    from wiki.staleness import (  # type: ignore[assignment]
        DEFAULT_RULES,
        StalenessLinter,
        StalenessReport,
        StalenessRule,
    )
except Exception:  # pragma: no cover
    StalenessLinter = None  # type: ignore[assignment]
    StalenessReport = None  # type: ignore[assignment]
    StalenessRule = None  # type: ignore[assignment]
    DEFAULT_RULES = None  # type: ignore[assignment]

try:
    from wiki.confluence_sync import (  # type: ignore[assignment]
        ConfluenceConfig,
        ConfluenceSync,
        ConfluenceSyncResult,
    )
except Exception:  # pragma: no cover
    ConfluenceSync = None  # type: ignore[assignment]
    ConfluenceConfig = None  # type: ignore[assignment]
    ConfluenceSyncResult = None  # type: ignore[assignment]

try:
    from wiki.signoz_sync import (  # type: ignore[assignment]
        SignozConfig,
        SignozSync,
        SignozSyncResult,
    )
except Exception:  # pragma: no cover
    SignozSync = None  # type: ignore[assignment]
    SignozConfig = None  # type: ignore[assignment]
    SignozSyncResult = None  # type: ignore[assignment]

try:
    from wiki.publisher import (  # type: ignore[assignment]
        PublishResult,
        Publisher,
        PublisherConfig,
    )
except Exception:  # pragma: no cover
    Publisher = None  # type: ignore[assignment]
    PublisherConfig = None  # type: ignore[assignment]
    PublishResult = None  # type: ignore[assignment]
