"""Write-scope tool: slack_post.

Sends a Slack message. Opt-in via ``load_write=True``.
"""

from __future__ import annotations

from mcp.scoped_tool import scoped_tool


@scoped_tool("write")
def slack_post(channel: str, message: str) -> dict:
    """Post a message to a Slack channel.

    Skeleton implementation.
    """
    return {
        "status": "success",
        "tool": "slack_post",
        "channel": channel,
        "message_ts": "0000000000.000000",
    }


__all__ = ["slack_post"]
