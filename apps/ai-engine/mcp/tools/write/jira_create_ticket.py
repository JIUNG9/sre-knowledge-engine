"""Write-scope tool: jira_create_ticket.

Creates a Jira ticket. Opt-in via ``load_write=True``.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("write")
def jira_create_ticket(project: str, summary: str, description: str = "") -> dict:
    """Create a new Jira ticket.

    Skeleton implementation.
    """
    return {
        "status": "success",
        "tool": "jira_create_ticket",
        "project": project,
        "summary": summary,
        "ticket_key": f"{project}-0000",
    }


__all__ = ["jira_create_ticket"]
