"""Pytest conftest for guardrails tests.

Makes ``apps/ai-engine`` importable regardless of where pytest is launched.
"""

from __future__ import annotations

import sys
from pathlib import Path

AI_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

TEST_POLICY_PATH = Path(__file__).resolve().parent / "policies" / "test_policy.yaml"
DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "policies" / "default.yaml"
)
