"""Shared fixtures and path setup for MCP tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Make `from mcp.x import ...` work when pytest is invoked from the repo root.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))
