"""``@scoped_tool`` decorator.

Registers a tool function into the module-global ``ToolManifest`` at
import time. The scope determines whether the tool is ever surfaced to
the agent:

- ``"read"``    — default allow, loaded whenever ``load_read=True``
- ``"write"``   — opt-in, requires ``load_write=True``
- ``"blocked"`` — registered for auditability, NEVER surfaced

Example
-------
>>> from mcp.scoped_tool import scoped_tool
>>>
>>> @scoped_tool("read")
>>> def log_search(query: str) -> dict:
>>>     ...

The decorator is idempotent — reimporting a module does not double-register.
"""

from __future__ import annotations

from typing import Callable, Literal

from mcp.manifest import manifest


Scope = Literal["read", "write", "blocked"]


def scoped_tool(scope: Scope, name: str | None = None) -> Callable[[Callable], Callable]:
    """Decorator factory that registers a tool with the manifest.

    Args:
        scope: The scope bucket for this tool.
        name: Override for the tool name. Defaults to the function name.

    Returns:
        A decorator that returns the function unchanged after registration.
    """
    if scope not in ("read", "write", "blocked"):
        raise ValueError(
            f"Invalid scope {scope!r}. Must be 'read', 'write', or 'blocked'."
        )

    def _decorator(fn: Callable) -> Callable:
        manifest.register(fn, scope=scope, name=name)
        # Stash metadata for inspection (debuggers, docs, etc.).
        fn.__mcp_scope__ = scope  # type: ignore[attr-defined]
        fn.__mcp_name__ = name or fn.__name__  # type: ignore[attr-defined]
        return fn

    return _decorator


__all__ = ["scoped_tool"]
