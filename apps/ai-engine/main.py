"""Aegis AI Engine — FastAPI entry point.

The AI Engine is the core intelligence layer of the Aegis DevSecOps Command
Center. It provides endpoints for incident investigation, log/metric analysis,
and interfaces with Claude API via MCP tools for autonomous SRE workflows.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze, health, investigate, logs, mcp

logger = logging.getLogger("aegis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info("Aegis AI Engine started")
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
