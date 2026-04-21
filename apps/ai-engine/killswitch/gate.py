"""``killswitch_gate`` — decorator that blocks tool execution when tripped.

Wrap every MCP tool handler (or any other dangerous call) with
:func:`killswitch_gate`. At call time the decorator asks a shared
:class:`KillSwitch` instance if the switch is active and, if so, raises
:class:`KillSwitchTripped` **before** the wrapped function executes.

Both sync and async callables are supported — the decorator detects which
kind was wrapped via :func:`inspect.iscoroutinefunction`.

The gate uses a lazily-constructed module-level :class:`KillSwitch` so that
hot-path tools do not pay the backend-probe cost on every call. Tests can
inject their own switch via :func:`set_killswitch` (re-exported as a public
helper for app wiring too).
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from killswitch.switch import KillSwitch

logger = logging.getLogger("aegis.killswitch.gate")

F = TypeVar("F", bound=Callable[..., Any])


class KillSwitchTripped(RuntimeError):
    """Raised when a ``killswitch_gate``-wrapped call fires while tripped.

    The ``status`` attribute carries the :class:`KillSwitchStatus` snapshot so
    callers (e.g. MCP server) can surface reason/operator in their response.
    """

    def __init__(self, status: Any) -> None:
        self.status = status
        reason = getattr(status, "reason", None) or "no reason given"
        operator = getattr(status, "operator", None) or "unknown"
        super().__init__(
            f"Aegis kill switch is ACTIVE (tripped by {operator}: {reason}). "
            f"Run `aegis release` to clear."
        )


_shared_switch: KillSwitch | None = None


def get_killswitch() -> KillSwitch:
    """Return (and lazily construct) the process-wide :class:`KillSwitch`."""
    global _shared_switch
    if _shared_switch is None:
        _shared_switch = KillSwitch()
    return _shared_switch


def set_killswitch(switch: KillSwitch | None) -> None:
    """Override the process-wide switch. Pass ``None`` to reset."""
    global _shared_switch
    _shared_switch = switch


def killswitch_gate(
    switch: KillSwitch | None = None,
    *,
    tool_name: str | None = None,
) -> Callable[[F], F]:
    """Decorator factory that enforces the kill switch.

    Args:
        switch: Explicit switch to consult. If omitted, the process-wide
            switch from :func:`get_killswitch` is used.
        tool_name: Optional tool name for log correlation. Defaults to the
            wrapped function's ``__qualname__``.

    Raises:
        KillSwitchTripped: When the switch is active at call time.
    """

    def decorator(func: F) -> F:
        name = tool_name or func.__qualname__
        is_coro = inspect.iscoroutinefunction(func)

        if is_coro:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                _check(switch, name)
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _check(switch, name)
            return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _check(switch: KillSwitch | None, tool_name: str) -> None:
    ks = switch or get_killswitch()
    if ks.is_active():
        status = ks.status()
        logger.critical(
            "Kill switch BLOCKED tool=%s operator=%s reason=%s",
            tool_name,
            getattr(status, "operator", None),
            getattr(status, "reason", None),
        )
        raise KillSwitchTripped(status)
