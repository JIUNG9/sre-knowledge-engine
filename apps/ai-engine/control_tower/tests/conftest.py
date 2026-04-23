"""Shared fixtures for control_tower tests.

Adds the ``apps/ai-engine`` directory to ``sys.path`` so ``import
control_tower`` resolves regardless of where pytest is launched.
"""

from __future__ import annotations

import sys
from pathlib import Path

_AI_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE_ROOT))
