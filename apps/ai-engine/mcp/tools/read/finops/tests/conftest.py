"""Shared fixtures for the finops tool test suite.

Adds the ai-engine root to ``sys.path`` so ``from mcp.x import y``
works regardless of whether pytest is invoked from the repo root or
from within this package.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_AI_ENGINE = Path(__file__).resolve().parents[5]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))

from mcp.tools.read.finops import config as finops_config  # noqa: E402


@pytest.fixture(autouse=True)
def reset_finops_config():
    """Reset the FinOpsConfig singleton between tests."""
    finops_config.reset_config()
    yield
    finops_config.reset_config()
