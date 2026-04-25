"""Configuration for the Aegis FinOps MCP tool suite.

``FinOpsConfig`` is the single source of truth for how the finops
tools reach their backends. All values default to safe, empty
placeholders so the package imports cleanly even on a fresh clone
with zero credentials configured.

Environment variables read (all optional)::

    AEGIS_FINOPS_AWS_REGION          AWS region for Cost Explorer (default us-east-1)
    AEGIS_FINOPS_AWS_PROFILE         Optional AWS profile name. If unset,
                                     boto3 uses the default credential chain.
    AEGIS_FINOPS_OPENCOST_URL        Base URL of the OpenCost API
                                     (e.g. http://opencost.opencost.svc.cluster.local:9003)
    AEGIS_FINOPS_KUBECOST_URL        Base URL of the Kubecost API
                                     (e.g. http://kubecost-cost-analyzer.kubecost.svc.cluster.local:9090)
    AEGIS_FINOPS_DEFAULT_WINDOW      Default query window (e.g. "7d", "30d").
    AEGIS_FINOPS_HTTP_TIMEOUT_S      HTTP timeout in seconds for OpenCost/Kubecost.

Note
----
The `acme-corp` name is a generic placeholder used only in docs and
tests — no employer-specific values appear here.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


class FinOpsConfig(BaseModel):
    """Cross-backend configuration for the Aegis FinOps tools."""

    # AWS Cost Explorer
    aws_region: str = Field(
        default_factory=lambda: os.getenv("AEGIS_FINOPS_AWS_REGION", "us-east-1")
    )
    aws_profile: str | None = Field(
        default_factory=lambda: os.getenv("AEGIS_FINOPS_AWS_PROFILE") or None
    )

    # OpenCost
    opencost_url: str | None = Field(
        default_factory=lambda: os.getenv("AEGIS_FINOPS_OPENCOST_URL") or None,
        description=(
            "Base URL of the OpenCost service, e.g. "
            "'http://opencost.opencost.svc.cluster.local:9003'."
        ),
    )

    # Kubecost
    kubecost_url: str | None = Field(
        default_factory=lambda: os.getenv("AEGIS_FINOPS_KUBECOST_URL") or None,
        description=(
            "Base URL of the Kubecost service, e.g. "
            "'http://kubecost-cost-analyzer.kubecost.svc.cluster.local:9090'."
        ),
    )

    # Defaults for composite tools
    default_window: str = Field(
        default_factory=lambda: os.getenv("AEGIS_FINOPS_DEFAULT_WINDOW", "7d")
    )
    http_timeout_s: float = Field(
        default_factory=lambda: float(
            os.getenv("AEGIS_FINOPS_HTTP_TIMEOUT_S", "10.0")
        )
    )

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #

    def opencost_endpoint(self, path: str) -> str | None:
        """Return a fully-qualified OpenCost URL, or None if not configured."""
        if not self.opencost_url:
            return None
        base = self.opencost_url.rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def kubecost_endpoint(self, path: str) -> str | None:
        """Return a fully-qualified Kubecost URL, or None if not configured."""
        if not self.kubecost_url:
            return None
        base = self.kubecost_url.rstrip("/")
        return f"{base}/{path.lstrip('/')}"


# ---------------------------------------------------------------------- #
# Process-wide singleton (test-overridable)
# ---------------------------------------------------------------------- #

_config: FinOpsConfig | None = None


def get_config() -> FinOpsConfig:
    """Return the current :class:`FinOpsConfig`, constructing if needed."""
    global _config
    if _config is None:
        _config = FinOpsConfig()
    return _config


def set_config(config: FinOpsConfig) -> None:
    """Install a process-wide config. Used by tests and FastAPI startup."""
    global _config
    _config = config


def reset_config() -> None:
    """Test helper — clear the singleton so env vars are re-read."""
    global _config
    _config = None


def unavailable_response(
    tool: str,
    backend: str,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a uniform 503-style response for unconfigured backends.

    Returning a dict (rather than raising) is deliberate: the agent
    should be able to reason over "this backend is not configured"
    and fall back to another provider without an exception breaking
    the tool_use round-trip.
    """
    payload: dict[str, Any] = {
        "status": "unavailable",
        "tool": tool,
        "backend": backend,
        "http_status": 503,
        "reason": reason,
    }
    if extra:
        payload.update(extra)
    return payload


__all__ = [
    "FinOpsConfig",
    "get_config",
    "set_config",
    "reset_config",
    "unavailable_response",
]
