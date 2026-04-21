"""Write-scope MCP tools.

Importing this package triggers registration of every write-scope tool
with the ``ToolManifest``. These tools cause real-world side effects
(Slack posts, Jira tickets) and are opt-in via ``MCPScopeConfig.load_write``.
"""

from mcp.tools.write import jira_create_ticket, slack_post  # noqa: F401

__all__ = ["jira_create_ticket", "slack_post"]
