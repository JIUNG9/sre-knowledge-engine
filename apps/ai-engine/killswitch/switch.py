"""KillSwitch — the actual trip/release state machine.

Two backends are supported:

1. ``redis`` (default) — ``SET``/``GET``/``DEL`` on a small JSON blob at
   ``state_key``. Reads are a single ``GET`` with a tight timeout so the
   hot path stays under 5ms.
2. ``file`` — a single flag file on disk. Present = tripped, absent = clear.
   Reads use ``os.stat`` so they are essentially free. This is the automatic
   fallback if the Redis client cannot be constructed / reached.

Every trip / release / fallback appends a structured event to a JSONL audit
log (default: ``./aegis-audit.jsonl``). The audit log is append-only and
never read back by the switch — it exists for forensics.

The switch is safe to instantiate many times: it is effectively stateless
beyond its configuration.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from killswitch.config import KillSwitchConfig

logger = logging.getLogger("aegis.killswitch")


# Redis is an optional dep at runtime — we import lazily so that environments
# without redis-py (or without a reachable Redis) still work via the file
# backend.
try:  # pragma: no cover - import guard
    import redis as _redis  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    _redis = None  # type: ignore[assignment]


_REDIS_OP_TIMEOUT_SECONDS = 0.05  # 50ms socket timeout; reads target <5ms.


@dataclass
class KillSwitchStatus:
    """Structured status snapshot returned by :meth:`KillSwitch.status`."""

    active: bool
    backend: str
    reason: str | None = None
    operator: str | None = None
    tripped_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KillSwitch:
    """Redis-backed emergency stop with a local-file fallback.

    The switch is the single source of truth for "should the agent run?". It
    is consumed by :func:`killswitch.gate.killswitch_gate`.

    Args:
        config: Optional :class:`KillSwitchConfig`. If omitted, one is built
            from environment variables.

    Attributes:
        config: Active configuration.
        backend: The backend actually in use — may be ``file`` even if the
            config requested ``redis`` (automatic fallback).
    """

    def __init__(self, config: KillSwitchConfig | None = None) -> None:
        self.config = config or KillSwitchConfig()
        self._redis_client: Any = None
        self.backend: str = self._initialize_backend()

    # ------------------------------------------------------------------ #
    # Backend initialization
    # ------------------------------------------------------------------ #

    def _initialize_backend(self) -> str:
        """Pick the concrete backend, falling back to ``file`` on failure."""
        requested = self.config.backend
        if requested == "file":
            # Set backend early so _audit_event can see it.
            self.backend = "file"
            return "file"

        if _redis is None:
            self.backend = "file"
            logger.warning(
                "redis-py not installed; falling back to file backend at %s",
                self.config.file_backend_path,
            )
            self._audit_event(
                "backend_fallback",
                operator="system",
                reason="redis-py not importable",
            )
            return "file"

        try:
            client = _redis.Redis.from_url(
                self.config.redis_url,
                socket_timeout=_REDIS_OP_TIMEOUT_SECONDS,
                socket_connect_timeout=_REDIS_OP_TIMEOUT_SECONDS,
                decode_responses=True,
            )
            # Cheap connectivity check — if this fails we demote to file.
            client.ping()
            self._redis_client = client
            self.backend = "redis"
            return "redis"
        except Exception as exc:  # noqa: BLE001 — we genuinely want any failure
            self.backend = "file"
            logger.warning(
                "Redis unreachable at %s (%s); falling back to file backend",
                self.config.redis_url,
                exc,
            )
            self._audit_event(
                "backend_fallback",
                operator="system",
                reason=f"redis unreachable: {exc}",
            )
            return "file"

    # Test hook: allow injection of an already-constructed redis client. This
    # keeps production code free of test-only branches while letting the
    # fakeredis-based tests skip the real Redis connection attempt.
    @classmethod
    def with_redis_client(
        cls, client: Any, config: KillSwitchConfig | None = None
    ) -> "KillSwitch":
        """Construct a :class:`KillSwitch` around a pre-built Redis client.

        Used primarily by tests with ``fakeredis`` so that the switch does
        not try to open a real socket.
        """
        instance = cls.__new__(cls)
        instance.config = config or KillSwitchConfig()
        instance._redis_client = client
        instance.backend = "redis"
        return instance

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def is_active(self) -> bool:
        """Return ``True`` when the switch is tripped.

        Designed to be cheap enough to call on every tool invocation
        (target: <5ms). Any backend error is treated as "fail-safe": if we
        genuinely cannot determine state, we return ``False`` and log — but
        we also keep the agent running rather than deadlocking it on a
        monitoring outage. The gate decorator pairs this with a retry at
        the tool boundary so a transient glitch does not block the fleet.
        """
        start = time.monotonic()
        try:
            if self.backend == "redis":
                value = self._redis_client.get(self.config.state_key)
                return value is not None
            return self.config.file_backend_path.exists()
        except Exception as exc:  # noqa: BLE001
            logger.error("Kill switch read failed on %s backend: %s", self.backend, exc)
            return False
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > 5:
                logger.warning(
                    "Kill switch is_active() took %.1fms (target <5ms)", elapsed_ms
                )

    def trip(self, reason: str, operator: str) -> KillSwitchStatus:
        """Activate the kill switch.

        Args:
            reason: Human-readable reason, stored alongside the state blob
                and in the audit log.
            operator: Who tripped it (e.g. ``june.gu``, ``pagerduty``).

        Returns:
            A :class:`KillSwitchStatus` describing the post-trip state.
        """
        if not reason:
            raise ValueError("trip() requires a non-empty reason")
        if not operator:
            raise ValueError("trip() requires a non-empty operator")

        payload = {
            "active": True,
            "reason": reason,
            "operator": operator,
            "tripped_at": _utc_now(),
        }

        if self.backend == "redis":
            try:
                self._redis_client.set(self.config.state_key, json.dumps(payload))
            except Exception as exc:  # noqa: BLE001
                logger.error("Redis trip failed: %s — writing file fallback", exc)
                self._write_file_state(payload)
        else:
            self._write_file_state(payload)

        self._audit_event("trip", operator=operator, reason=reason)
        logger.critical(
            "KILL SWITCH TRIPPED by %s: %s (backend=%s)",
            operator,
            reason,
            self.backend,
        )
        return KillSwitchStatus(
            active=True,
            backend=self.backend,
            reason=reason,
            operator=operator,
            tripped_at=payload["tripped_at"],
        )

    def release(self, operator: str) -> KillSwitchStatus:
        """Clear the kill switch.

        Args:
            operator: Who is releasing it. Recorded in the audit log.

        Returns:
            A :class:`KillSwitchStatus` describing the post-release state.
        """
        if not operator:
            raise ValueError("release() requires a non-empty operator")

        if self.backend == "redis":
            try:
                self._redis_client.delete(self.config.state_key)
            except Exception as exc:  # noqa: BLE001
                logger.error("Redis release failed: %s", exc)
        # Always clear any file-backend flag, even when on redis — so a prior
        # fallback state cannot "resurrect" the switch after release.
        if self.config.file_backend_path.exists():
            try:
                self.config.file_backend_path.unlink()
            except OSError as exc:
                logger.error("Failed to remove file backend flag: %s", exc)

        self._audit_event("release", operator=operator, reason="released")
        logger.warning("Kill switch RELEASED by %s", operator)
        return KillSwitchStatus(active=False, backend=self.backend)

    def status(self) -> KillSwitchStatus:
        """Return a rich status snapshot (including reason/operator if tripped)."""
        if self.backend == "redis":
            try:
                raw = self._redis_client.get(self.config.state_key)
            except Exception as exc:  # noqa: BLE001
                logger.error("Redis status read failed: %s", exc)
                raw = None
            if not raw:
                return KillSwitchStatus(active=False, backend=self.backend)
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                data = None
            if not isinstance(data, dict):
                # Legacy/unstructured value (e.g. `redis-cli SET ... 1`).
                return KillSwitchStatus(
                    active=True,
                    backend=self.backend,
                    reason="unstructured state value",
                )
            return KillSwitchStatus(
                active=bool(data.get("active", True)),
                backend=self.backend,
                reason=data.get("reason"),
                operator=data.get("operator"),
                tripped_at=data.get("tripped_at"),
            )

        # file backend
        if not self.config.file_backend_path.exists():
            return KillSwitchStatus(active=False, backend=self.backend)
        try:
            data = json.loads(self.config.file_backend_path.read_text())
        except (OSError, ValueError):
            return KillSwitchStatus(
                active=True, backend=self.backend, reason="unreadable flag file"
            )
        return KillSwitchStatus(
            active=bool(data.get("active", True)),
            backend=self.backend,
            reason=data.get("reason"),
            operator=data.get("operator"),
            tripped_at=data.get("tripped_at"),
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _write_file_state(self, payload: dict[str, Any]) -> None:
        path = self.config.file_backend_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload))
        except OSError as exc:
            logger.error("Failed to persist kill switch file state: %s", exc)

    def _audit_event(self, event: str, *, operator: str, reason: str) -> None:
        entry = {
            "timestamp": _utc_now(),
            "event": event,
            "operator": operator,
            "reason": reason,
            "backend": self.backend,
            "pid": os.getpid(),
        }
        path = self.config.audit_log_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError as exc:
            logger.error("Failed to append kill switch audit event: %s", exc)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
