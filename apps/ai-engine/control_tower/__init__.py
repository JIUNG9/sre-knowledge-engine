"""Aegis Claude Control Tower — Layer 3.

The control tower is the brain of Aegis. It takes an alert (or SRE
question), pulls the right context out of the L1 wiki and L2 telemetry
layers, routes the prompt through the LLM router (which picks Ollama
vs Claude based on sensitivity), parses the response into a structured
:class:`Investigation`, and proposes actions through the Layer 4
guardrails ladder.

Three modes trade depth for cost:

* ``eco`` — Haiku-class, ~4k context, one LLM call, fast triage
* ``standard`` — Sonnet-class, ~16k context, up to 2 calls, telemetry
* ``deep`` — Opus-class, ~64k context, up to 3 calls, pattern analysis

Typical usage::

    from control_tower import ControlTower, Alert

    tower = ControlTower(
        llm_router=router,
        wiki=wiki_adapter,
        log_fetcher=logs,
        metric_fetcher=metrics,
        guardrails=guardrails_engine,
        killswitch=killswitch,
    )
    investigation = await tower.investigate(
        Alert(service="payment-svc", severity="critical"),
        mode="standard",
    )

The :class:`control_tower.api.control_tower_router` is a ready-to-mount
FastAPI router with ``/investigate`` + ``/modes`` + ``/lookup`` endpoints.
The application entry point is expected to mount it via
``app.include_router(control_tower_router)``; that wiring is left for
a follow-up PR so Layer 3 can land independently.
"""

from __future__ import annotations

from .action import propose_action
from .api import (
    InvestigateRequest,
    ModeInfo,
    control_tower_router,
    get_control_tower,
)
from .config import ControlTowerConfig, InvestigationModeName
from .context_builder import ContextBuilder, WikiAdapter
from .investigation import (
    Alert,
    Context,
    Evidence,
    Hypothesis,
    Investigation,
    InvestigationMode,
    InvestigationUsage,
    LogSummary,
    MetricSummary,
    PatternFinding,
    ProposedAction,
    Severity,
    TraceHint,
    WikiSnippet,
)
from .modes import DEEP, ECO, STANDARD, ModeSpec, all_modes, get_mode_spec
from .orchestrator import ControlTower

__all__ = [
    # Orchestrator
    "ControlTower",
    "ControlTowerConfig",
    # Data shapes
    "Alert",
    "Context",
    "Evidence",
    "Hypothesis",
    "Investigation",
    "InvestigationMode",
    "InvestigationModeName",
    "InvestigationUsage",
    "LogSummary",
    "MetricSummary",
    "PatternFinding",
    "ProposedAction",
    "Severity",
    "TraceHint",
    "WikiSnippet",
    # Modes
    "ECO",
    "STANDARD",
    "DEEP",
    "ModeSpec",
    "all_modes",
    "get_mode_spec",
    # Builders
    "ContextBuilder",
    "WikiAdapter",
    "propose_action",
    # API
    "InvestigateRequest",
    "ModeInfo",
    "control_tower_router",
    "get_control_tower",
]
