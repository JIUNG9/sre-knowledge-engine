"""Aegis Layer 0.6 — Honey Token Beacon.

Public API:

- `HoneyToken`            — dataclass representing an emitted token.
- `HoneyTokenGenerator`   — factory that creates and persists tokens.
- `HoneyTokenDetector`    — alias of `OutboundScanner` for clarity at
  call-sites (e.g. `detector.scan(llm_response)`).
- `OutboundScanner`       — Aho-Corasick scanner over registered tokens.
- `HoneyTokenHit`         — dataclass for a single match.
- `HoneyTokenRegistry`    — CRUD over the SQLite registry.
- `HoneyTokenConfig`      — runtime configuration.
- `seed_vault`            — idempotently seed tokens into a vault.
- `fire_alert`            — dispatch OTel + webhook + stderr alerts.
"""

from .alert import fire as fire_alert
from .config import HoneyTokenConfig, get_config, set_config
from .generator import HoneyToken, HoneyTokenGenerator, TokenCategory
from .registry import HoneyTokenRegistry
from .scanner import HoneyTokenHit, OutboundScanner, get_default_scanner
from .seeder import seed_vault

# Detector is an alias — the canonical scanner implementation lives in
# `scanner.py`, but integrators often prefer the "detector" noun.
HoneyTokenDetector = OutboundScanner

__all__ = [
    "HoneyToken",
    "HoneyTokenCategory",
    "HoneyTokenConfig",
    "HoneyTokenDetector",
    "HoneyTokenGenerator",
    "HoneyTokenHit",
    "HoneyTokenRegistry",
    "OutboundScanner",
    "TokenCategory",
    "fire_alert",
    "get_config",
    "get_default_scanner",
    "seed_vault",
    "set_config",
]

# Back-compat noun so external code can `from honeytokens import HoneyTokenCategory`.
HoneyTokenCategory = TokenCategory
