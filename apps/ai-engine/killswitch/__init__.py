"""Aegis Kill Switch — emergency stop for the AI agent.

Public API:
- :class:`KillSwitch` — Redis-backed (with file fallback) emergency stop state.
- :func:`killswitch_gate` — decorator that blocks MCP tool execution when tripped.
- :class:`KillSwitchTripped` — raised when a gated tool is called while active.
- :class:`KillSwitchConfig` — configuration (Redis URL, backend, AWS revoke opts).

Design goals (Layer 0.3):
- State checks must complete in under 5ms so they can sit on the hot path.
- Every trip / release is appended to a persistent JSONL audit log.
- AWS session revocation is OFF by default — explicit opt-in only.
- Graceful degradation: if Redis is down, automatically fall back to the local
  file backend and emit a warning.

Typical usage::

    from killswitch import KillSwitch, killswitch_gate

    @killswitch_gate()
    async def kubectl_action(params: dict) -> dict:
        ...

    ks = KillSwitch()
    if ks.is_active():
        ...  # refuse work
"""

from __future__ import annotations

from killswitch.config import KillSwitchConfig
from killswitch.gate import KillSwitchTripped, killswitch_gate
from killswitch.switch import KillSwitch, KillSwitchStatus

__all__ = [
    "KillSwitch",
    "KillSwitchConfig",
    "KillSwitchStatus",
    "KillSwitchTripped",
    "killswitch_gate",
]
