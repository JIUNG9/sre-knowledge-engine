"""FastAPI router for the Aegis Control Tower (Layer 3).

Exposes three endpoints under ``/api/v2`` (the legacy ``/api/v1/investigate``
in ``routers/investigate.py`` is the v3 mock-data implementation; v2 is
the real Control Tower so both can coexist during migration):

* ``POST /api/v2/investigate`` — run a new investigation.
* ``GET /api/v2/investigations/{id}`` — retrieve a cached investigation.
* ``GET /api/v2/modes`` — describe available modes.

The router is mounted by ``main.py``. Its ``get_control_tower``
dependency returns 503 until ``main.py``'s lifespan hook attaches a
real ``ControlTower`` instance (gated on ``AEGIS_CONTROL_TOWER`` env).

The router reads a :class:`ControlTower` instance from a dependency
function. By default the dependency raises 503 — callers in the app
entry point override it with ``app.dependency_overrides`` once they
have a configured tower (with LLM router, wiki, guardrails, etc.).
This keeps the router import-safe (no network at startup) while
still giving production code a clean wire-up point.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .config import InvestigationModeName
from .investigation import Alert, Investigation
from .modes import all_modes


class InvestigateRequest(BaseModel):
    """Body for ``POST /api/v1/investigate``."""

    alert: Alert
    mode: InvestigationModeName = Field(default="standard")


class ModeInfo(BaseModel):
    """Serialized mode spec for ``GET /api/v1/modes``."""

    name: str
    description: str
    preferred_model: str
    max_tokens: int
    temperature: float
    include_wiki: bool
    include_logs: bool
    include_metrics: bool
    include_traces: bool
    include_alert_history: bool
    run_pattern_analyzer: bool
    max_llm_calls: int
    tools: list[str]


control_tower_router = APIRouter(prefix="/api/v2", tags=["control-tower"])


# --------------------------------------------------------------------------- #
# Dependency
# --------------------------------------------------------------------------- #


def get_control_tower() -> Any:
    """Return the active :class:`ControlTower`.

    Default implementation raises 503 so importing the router never
    forces network configuration. The app entry point overrides this
    with a real factory via ``app.dependency_overrides``.
    """
    raise HTTPException(
        status_code=503,
        detail=(
            "control tower not configured; override "
            "`get_control_tower` in the FastAPI app"
        ),
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@control_tower_router.post(
    "/investigate",
    response_model=Investigation,
    summary="Run an investigation",
)
async def investigate_endpoint(
    body: InvestigateRequest,
    tower: Any = Depends(get_control_tower),
) -> Investigation:
    """Invoke ``ControlTower.investigate`` with the posted alert."""
    return await tower.investigate(body.alert, mode=body.mode)


@control_tower_router.get(
    "/investigations/{investigation_id}",
    response_model=Investigation,
    summary="Lookup a previous investigation",
)
def lookup_endpoint(
    investigation_id: str,
    tower: Any = Depends(get_control_tower),
) -> Investigation:
    """Retrieve a prior investigation by id or trace_id."""
    inv = tower.lookup(investigation_id)
    if inv is None:
        raise HTTPException(
            status_code=404,
            detail=f"investigation {investigation_id!r} not found",
        )
    return inv


@control_tower_router.get(
    "/modes",
    response_model=list[ModeInfo],
    summary="Describe available investigation modes",
)
def modes_endpoint() -> list[ModeInfo]:
    """List every registered mode + its static spec."""
    return [ModeInfo(**spec.to_dict()) for spec in all_modes()]
