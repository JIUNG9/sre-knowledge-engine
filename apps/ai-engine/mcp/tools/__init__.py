"""MCP tool definitions for the Aegis AI Engine.

Each module defines tool schemas following the Anthropic tool_use format:
- name: Unique tool identifier
- description: What the tool does (used by Claude to decide when to call it)
- input_schema: JSON Schema defining the tool's parameters
"""

from mcp.tools.infrastructure import INFRASTRUCTURE_TOOLS
from mcp.tools.observability import OBSERVABILITY_TOOLS
from mcp.tools.workflow import WORKFLOW_TOOLS

ALL_TOOLS = OBSERVABILITY_TOOLS + INFRASTRUCTURE_TOOLS + WORKFLOW_TOOLS

__all__ = ["ALL_TOOLS", "OBSERVABILITY_TOOLS", "INFRASTRUCTURE_TOOLS", "WORKFLOW_TOOLS"]
