"""Honey token generator.

Produces unique, tamper-evident tokens in several realistic shapes
(AWS access keys, email addresses, hostnames, DB passwords, API keys,
PEM blocks). Every token embeds an `AEGIS-HONEY-{sha256[:12]}` marker
so that a human scrubbing logs can distinguish it from a real secret
on close inspection, while automated scanners can detect it reliably.

The generator delegates persistence to `HoneyTokenRegistry` so callers
only need to use the high-level `create()` API.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import string
import time
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Literal, Optional

from .registry import HoneyTokenRegistry

TokenCategory = Literal[
    "aws_key",
    "email",
    "hostname",
    "db_password",
    "api_key",
    "pem_block",
]

_ALL_CATEGORIES: tuple[TokenCategory, ...] = (
    "aws_key",
    "email",
    "hostname",
    "db_password",
    "api_key",
    "pem_block",
)

MARKER_PREFIX = "AEGIS-HONEY-"


@dataclass(frozen=True)
class HoneyToken:
    """An emitted honey token.

    `value` is the rendered string that will be seeded into the vault or
    agent prompt. `marker` is the canonical `AEGIS-HONEY-...` fingerprint
    which the scanner uses for Aho-Corasick matching — it is always a
    substring of `value`.
    """

    id: str
    category: TokenCategory
    value: str
    marker: str
    fingerprint: str
    created_at: float
    seeded_locations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["seeded_locations"] = list(self.seeded_locations)
        return d


def _rand_alnum(n: int, *, alphabet: str = string.ascii_uppercase + string.digits) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _short_hash() -> tuple[str, str]:
    """Return (marker, full-sha256) pair. Marker is AEGIS-HONEY-{12 hex}."""
    raw = secrets.token_bytes(32) + os.urandom(8) + str(time.time_ns()).encode()
    full = hashlib.sha256(raw).hexdigest()
    marker = f"{MARKER_PREFIX}{full[:12]}"
    return marker, full


def _render(category: TokenCategory, marker: str) -> str:
    """Render a realistic-looking secret containing the marker."""
    suffix = marker.split("-")[-1]  # 12 hex
    if category == "aws_key":
        # AWS access keys are 20 chars starting AKIA. We embed the marker on
        # a following `# ` comment so pasted context keeps the trap visible.
        ak = "AKIA" + _rand_alnum(16)
        sk = _rand_alnum(40, alphabet=string.ascii_letters + string.digits + "/+")
        return (
            f"aws_access_key_id={ak}\n"
            f"aws_secret_access_key={sk}\n"
            f"# {marker}"
        )
    if category == "email":
        local = f"svc-{suffix}"
        return f"{local}@aegis-honey.internal  # {marker}"
    if category == "hostname":
        return f"db-{suffix}.aegis-honey.internal  # {marker}"
    if category == "db_password":
        pw = _rand_alnum(24, alphabet=string.ascii_letters + string.digits + "!@#$%^&*")
        return f"POSTGRES_PASSWORD={pw}  # {marker}"
    if category == "api_key":
        key = f"sk-ha-{_rand_alnum(32, alphabet=string.ascii_letters + string.digits)}"
        return f"{key}  # {marker}"
    if category == "pem_block":
        body = "\n".join(
            _rand_alnum(64, alphabet=string.ascii_letters + string.digits + "+/")
            for _ in range(8)
        )
        return (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            f"{body}\n"
            f"{marker}\n"
            "-----END RSA PRIVATE KEY-----"
        )
    raise ValueError(f"unknown category: {category}")


class HoneyTokenGenerator:
    """Create and persist honey tokens."""

    def __init__(self, registry: Optional[HoneyTokenRegistry] = None) -> None:
        self._registry = registry or HoneyTokenRegistry()

    @property
    def registry(self) -> HoneyTokenRegistry:
        return self._registry

    def create(self, category: TokenCategory) -> HoneyToken:
        if category not in _ALL_CATEGORIES:
            raise ValueError(
                f"invalid category {category!r}; must be one of {_ALL_CATEGORIES}"
            )
        marker, full = _short_hash()
        value = _render(category, marker)
        token = HoneyToken(
            id=marker,
            category=category,
            value=value,
            marker=marker,
            fingerprint=full,
            created_at=time.time(),
            seeded_locations=tuple(),
        )
        self._registry.insert(token)
        return token

    def create_batch(
        self,
        categories: Iterable[TokenCategory],
    ) -> List[HoneyToken]:
        return [self.create(c) for c in categories]

    def all_categories(self) -> tuple[TokenCategory, ...]:
        return _ALL_CATEGORIES
