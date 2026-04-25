"""Shared pytest fixtures for the scheduler test suite.

We deliberately keep the path tweak local to this conftest so the tests
work both via ``pytest scheduler/tests`` and via the project-level
``pytest`` invocation in CI.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Ensure ``from scheduler.x import ...`` resolves to apps/ai-engine.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))


# ---- Test stubs ------------------------------------------------------- #


class FakeKillSwitch:
    """Minimal kill switch test double.

    Mirrors the only method the runner calls (``is_active``). ``raise_on_check``
    flips the switch into raising so we can verify graceful degradation.
    """

    def __init__(self, active: bool = False, raise_on_check: bool = False) -> None:
        self.active = active
        self.raise_on_check = raise_on_check
        self.calls = 0

    def is_active(self) -> bool:  # noqa: D401
        self.calls += 1
        if self.raise_on_check:
            raise RuntimeError("backend unreachable")
        return self.active


@pytest.fixture
def fake_killswitch() -> FakeKillSwitch:
    """Default fixture: a clear (non-tripped) switch."""
    return FakeKillSwitch(active=False)


@pytest.fixture
def tripped_killswitch() -> FakeKillSwitch:
    """A pre-tripped switch — every job must skip when this is wired."""
    return FakeKillSwitch(active=True)


# ---- Event loop fixture ---------------------------------------------- #


@pytest.fixture
def event_loop():
    """Function-scoped loop so APScheduler tests don't leak handles.

    pytest-asyncio's default ``function`` scope already provides this,
    but stating it explicitly keeps the fixture deterministic across
    pytest-asyncio version bumps.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
