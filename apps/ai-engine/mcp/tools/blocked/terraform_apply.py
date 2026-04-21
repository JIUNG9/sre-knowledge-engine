"""Blocked-scope tool: terraform_apply.

This tool is DEFINED but NEVER SURFACED. The manifest filters blocked
tools at load time so no prompt injection can invoke it. The body
exists only to document what the tool would do and to satisfy any
direct import.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("blocked")
def terraform_apply(workspace: str, auto_approve: bool = False) -> dict:
    """Would run ``terraform apply`` — permanently blocked.

    Raising here is cheap insurance: if the manifest is ever bypassed,
    the call still fails loud.
    """
    raise PermissionError(
        "terraform_apply is in the blocked-scope tool set and cannot be "
        "invoked by the agent. See mcp/SCOPING.md."
    )


__all__ = ["terraform_apply"]
