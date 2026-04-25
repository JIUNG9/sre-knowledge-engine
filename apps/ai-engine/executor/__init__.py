"""Aegis Layer 4 executor (Phase 2.5).

Public API:
    Executor            — main dispatcher
    ExecutorConfig      — env-driven config
    ExecutionResult     — pydantic result of one dispatch
    AuditLogger         — JSONL audit writer
    KubectlWrapper      — kubectl wrapper (read-only + scale + restart)
    TerraformWrapper    — terraform wrapper (plan-only by default)
    AwsCliWrapper       — aws CLI wrapper (read-only by default)

The executor is the keystone of Aegis self-healing: every other layer
*proposes*, the executor *runs*. Every gate that has already said yes
(risk, policy, approvals) is rechecked at this layer because this is
where commands actually mutate real infrastructure.

Wired into FastAPI in ``main.py`` only when ``AEGIS_EXECUTOR_ENABLED=1``.
Tests, CI, and cold starts never run real commands.
"""

from __future__ import annotations

from .api import executor_router, get_executor
from .audit import AuditLogger, ExecutorAuditRecord
from .config import DEFAULT_ALLOWED_VERBS, ExecutorConfig
from .executor import Executor
from .result import ExecutionResult
from .wrappers import AwsCliWrapper, KubectlWrapper, TerraformWrapper, Wrapper

__all__ = [
    "AuditLogger",
    "AwsCliWrapper",
    "DEFAULT_ALLOWED_VERBS",
    "ExecutionResult",
    "Executor",
    "ExecutorAuditRecord",
    "ExecutorConfig",
    "KubectlWrapper",
    "TerraformWrapper",
    "Wrapper",
    "executor_router",
    "get_executor",
]
