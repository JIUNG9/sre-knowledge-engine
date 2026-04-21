"""Honey token subsystem configuration.

Reads environment variables via pydantic-settings when available, otherwise
falls back to dataclass defaults so the package is importable without the
full Aegis dependency stack (useful for CI and unit tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class HoneyTokenConfig:
    """Runtime configuration for the honey token subsystem.

    Attributes:
        enabled: Master switch. If False, generator still works but the
            scanner and alerting hooks become no-ops.
        registry_path: Path to the SQLite file persisting generated tokens.
        webhook_url: Optional HTTPS endpoint to POST hit alerts to.
        seed_demo_vault: If True, the bootstrap path will call
            `seed_vault` against the bundled demo Obsidian vault on startup.
        otel_service_name: Service name attached to alert spans.
        log_registry_contents: MUST remain False in production. If True,
            token values may appear in debug logs, defeating the trap.
    """

    enabled: bool = True
    registry_path: str = "./honeytokens.db"
    webhook_url: Optional[str] = None
    seed_demo_vault: bool = True
    otel_service_name: str = "aegis-ai-engine"
    log_registry_contents: bool = False


_config: HoneyTokenConfig = HoneyTokenConfig()


def get_config() -> HoneyTokenConfig:
    """Return the process-wide honey token config."""
    return _config


def set_config(cfg: HoneyTokenConfig) -> None:
    """Override the process-wide config (primarily for tests)."""
    global _config
    _config = cfg
