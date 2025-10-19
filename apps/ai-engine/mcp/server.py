"""MCP server definition for the Aegis AI Engine.

This module defines the MCP server that exposes observability, infrastructure,
and workflow tools to Claude during agent-driven investigations. The server
aggregates all tool definitions and provides a unified interface for the
AI agents to interact with external systems.
"""

from mcp.tools.infrastructure import INFRASTRUCTURE_TOOLS
from mcp.tools.observability import OBSERVABILITY_TOOLS
from mcp.tools.workflow import WORKFLOW_TOOLS


class MCPServer:
    """MCP server that provides tools for Claude AI agents.

    The server exposes three categories of tools:
    - Observability: Query logs, metrics, traces, and SigNoz dashboards
    - Infrastructure: Read Kubernetes state, describe AWS resources, run Terraform
    - Workflow: Notify Slack, create Jira tickets, open PRs, search runbooks
    """

    def __init__(self):
        self.tools: list[dict] = []
        self._register_tools()

    def _register_tools(self):
        """Register all available MCP tools."""
        self.tools.extend(OBSERVABILITY_TOOLS)
        self.tools.extend(INFRASTRUCTURE_TOOLS)
        self.tools.extend(WORKFLOW_TOOLS)

    def get_tools(self) -> list[dict]:
        """Return all registered tool schemas for Claude API tool_use."""
        return self.tools

    def get_tool(self, name: str) -> dict | None:
        """Look up a single tool schema by name."""
        for tool in self.tools:
            if tool["name"] == name:
                return tool
        return None

    def get_tools_requiring_approval(self) -> list[dict]:
        """Return tools that require human approval before execution."""
        return [t for t in self.tools if t.get("requires_approval", False)]


# Singleton instance
mcp_server = MCPServer()
