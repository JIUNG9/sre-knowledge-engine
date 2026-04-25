"""Typed command wrappers for the Aegis executor.

Each wrapper translates a :class:`ProposedAction` into a structured
argv list for a specific CLI (kubectl / terraform / aws). They never
accept arbitrary shell — only typed args drawn from a hard-coded
allow-list. Adding a new wrapper or verb requires a code change AND
configuration opt-in via :class:`ExecutorConfig.allowed_verbs`.

Public API:
    Wrapper          — abstract base; implementations live alongside
    KubectlWrapper   — read-only Kubernetes verbs by default
    TerraformWrapper — plan-only by default; apply gated; destroy NEVER
    AwsCliWrapper    — describe-* / list-* / get-* only
"""

from __future__ import annotations

from .aws import AwsCliWrapper
from .base import Wrapper, WrapperError
from .kubectl import KubectlWrapper
from .terraform import TerraformWrapper

__all__ = [
    "AwsCliWrapper",
    "KubectlWrapper",
    "TerraformWrapper",
    "Wrapper",
    "WrapperError",
]
