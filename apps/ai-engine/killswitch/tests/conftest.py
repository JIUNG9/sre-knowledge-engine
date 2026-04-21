"""Pytest configuration for killswitch tests.

Ensures ``apps/ai-engine`` is importable when tests are run via ``pytest``
from the repo root or from inside the ai-engine directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

AI_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))
