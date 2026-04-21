# Copyright 2026 June Gu
# Licensed under the Apache License, Version 2.0.
"""Shared test fixtures for the connectors package.

Adds the ``apps/ai-engine`` directory to ``sys.path`` so ``import
connectors`` resolves regardless of where pytest is invoked from.
"""

from __future__ import annotations

import sys
from pathlib import Path


_AI_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE_ROOT))
