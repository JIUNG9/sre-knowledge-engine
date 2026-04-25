"""Aegis AI Engine — FastAPI entry point.

The AI Engine is the core intelligence layer of the Aegis DevSecOps Command
Center. It provides endpoints for incident investigation, log/metric analysis,
and interfaces with Claude API via MCP tools for autonomous SRE workflows.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from control_tower.api import control_tower_router, get_control_tower
from routers import analyze, health, investigate, logs, mcp, wiki

# Layer 0.1 — PII Redaction Proxy for Claude API.
#
# To enable PII redaction for every outbound Claude call, wrap the SDK client
# at instantiation time. Because the proxy is a drop-in for
# ``anthropic.Anthropic`` (same ``messages.create`` signature, same response
# shape, streaming preserved), no downstream code needs to change:
#
#     import anthropic
#     from proxy import AnthropicProxy, PIIProxyConfig
#
#     claude = AnthropicProxy(
#         anthropic.Anthropic(api_key=settings.anthropic_api_key),
#         PIIProxyConfig(),   # enabled=True by default
#     )
#     # ... hand ``claude`` to orchestrator / remediator / analyzer as usual.
#
# See ``apps/ai-engine/proxy/README.md`` for usage patterns.

logger = logging.getLogger("aegis")


def _build_control_tower():
    """Construct a ControlTower instance for production use.

    Lazy import keeps the FastAPI startup path lightweight when the
    Control Tower's heavier deps (anthropic SDK, ollama client) are
    not yet installed. Returns None if construction fails — the API
    layer falls back to the default 503 dependency.
    """
    try:
        from control_tower import ControlTower, ControlTowerConfig
    except Exception as exc:
        logger.warning("control tower unavailable (import): %s", exc)
        return None
    try:
        return ControlTower(config=ControlTowerConfig())
    except Exception as exc:
        logger.warning("control tower unavailable (init): %s", exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info("Aegis AI Engine started")

    # Layer 3 — Claude Control Tower. Build a tower if the env asks for
    # it and stash on app.state so the dependency below can return it.
    # Disabled by default so unit tests / CI / cold starts don't try to
    # connect to Anthropic. Set AEGIS_CONTROL_TOWER=1 to enable.
    if os.environ.get("AEGIS_CONTROL_TOWER", "").lower() in ("1", "true", "yes"):
        tower = _build_control_tower()
        if tower is not None:
            app.state.control_tower = tower
            app.dependency_overrides[get_control_tower] = lambda: tower
            logger.info("control tower attached to /api/v1/investigate")

    yield
    logger.info("Aegis AI Engine shutting down")


app = FastAPI(
    title="Aegis AI Engine",
    version="0.1.0",
    description="AI-Native DevSecOps Command Center — Intelligence Layer",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(investigate.router)
app.include_router(analyze.router)
app.include_router(logs.router)
app.include_router(mcp.router)
app.include_router(wiki.router)
# Layer 3 — Claude Control Tower. The dependency returns 503 until the
# lifespan hook above attaches a real ControlTower instance (gated on
# AEGIS_CONTROL_TOWER env). This keeps OpenAPI complete in dev while
# preventing accidental network calls at startup.
app.include_router(control_tower_router)
