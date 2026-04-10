"""MCP (Model Context Protocol) management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mcp.server import MCPServer

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])

mcp_server = MCPServer()

# ─── Audit log (in-memory) ────────────────────────────────────

_audit_log: list[dict] = []


class ToolExecuteRequest(BaseModel):
    """Request to execute an MCP tool (for testing)."""

    params: dict = {}


class AuditEntry(BaseModel):
    """Audit log entry for tool execution."""

    tool_name: str
    params: dict
    result_preview: str
    success: bool
    timestamp: str
    requires_approval: bool


# ─── Endpoints ────────────────────────────────────────────────


@router.get("/tools")
async def list_tools():
    """List all available MCP tools with their schemas."""
    tools = mcp_server.get_tools()
    return {
        "tools": tools,
        "total": len(tools),
        "categories": {
            "observability": [t for t in tools if t.get("category") == "observability"],
            "infrastructure": [t for t in tools if t.get("category") == "infrastructure"],
            "workflow": [t for t in tools if t.get("category") == "workflow"],
        },
    }


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get detailed information about a specific MCP tool."""
    tool = mcp_server.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return tool


@router.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, request: ToolExecuteRequest):
    """Execute an MCP tool (for testing/debugging).

    Note: WRITE tools require approval in production.
    This endpoint is for testing only.
    """
    tool = mcp_server.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    requires_approval = tool.get("requires_approval", False)

    # In production, WRITE tools would require Slack approval
    # For testing, we execute with mock results
    from datetime import datetime, timezone

    result = {
        "tool": tool_name,
        "params": request.params,
        "result": f"Mock execution result for {tool_name}",
        "requires_approval": requires_approval,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Log to audit trail
    _audit_log.append(
        {
            "tool_name": tool_name,
            "params": request.params,
            "result_preview": str(result["result"])[:200],
            "success": True,
            "timestamp": result["executed_at"],
            "requires_approval": requires_approval,
        }
    )

    return result


@router.get("/audit")
async def get_audit_log(limit: int = 50):
    """Get the tool execution audit log."""
    return {
        "entries": _audit_log[-limit:],
        "total": len(_audit_log),
    }


@router.get("/stats")
async def get_mcp_stats():
    """Get MCP server statistics."""
    tools = mcp_server.get_tools()
    return {
        "total_tools": len(tools),
        "read_tools": len([t for t in tools if not t.get("requires_approval", False)]),
        "write_tools": len([t for t in tools if t.get("requires_approval", False)]),
        "total_executions": len(_audit_log),
        "categories": ["observability", "infrastructure", "workflow"],
    }
