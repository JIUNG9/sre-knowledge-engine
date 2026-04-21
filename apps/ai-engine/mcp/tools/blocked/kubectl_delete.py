"""Blocked-scope tool: kubectl_delete.

Defined for documentation only. Never surfaced to the agent.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("blocked")
def kubectl_delete(resource: str, namespace: str = "default") -> dict:
    """Would run ``kubectl delete`` — permanently blocked."""
    raise PermissionError(
        "kubectl_delete is in the blocked-scope tool set and cannot be "
        "invoked by the agent. See mcp/SCOPING.md."
    )


__all__ = ["kubectl_delete"]
