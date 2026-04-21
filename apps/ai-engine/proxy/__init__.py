# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""Aegis Layer 0.1 — PII Redaction Proxy for the Claude API.

This module implements a reverse proxy that sits between Aegis and the
Anthropic Claude API. On outbound requests it detects PII (emails, IPv4/IPv6
addresses, AWS account IDs, access keys, internal hostnames, JWT/Bearer
tokens, PEM blocks, etc.) and replaces every occurrence with a deterministic
per-request placeholder (e.g. ``<EMAIL_1>``, ``<IP_2>``). On response from
Claude the placeholders are reverse-substituted back to the original values
before returning to the caller, so downstream code never sees a redacted
payload.

The proxy is default-on and fully in-process. No values are ever persisted
to disk. Mappings live in a thread-safe in-memory store with a configurable
TTL and are scoped per-request to prevent cross-request leakage.

Public API:
    :class:`AnthropicProxy`   — drop-in wrapper around ``anthropic.Anthropic``.
    :class:`PIIProxyConfig`   — Pydantic configuration.
    :class:`PIIDetector`      — detection engine (Presidio + regex hybrid).
    :class:`PlaceholderMapper` — reversible placeholder map with TTL.

Typical usage::

    from anthropic import Anthropic
    from proxy import AnthropicProxy, PIIProxyConfig

    client = AnthropicProxy(Anthropic(), PIIProxyConfig())
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": "logs from host db01.acme.internal"}],
    )
"""

from proxy.config import PIIProxyConfig
from proxy.detector import Detection, PIIDetector
from proxy.mapper import PlaceholderMapper
from proxy.proxy import AnthropicProxy

__all__ = [
    "AnthropicProxy",
    "Detection",
    "PIIDetector",
    "PIIProxyConfig",
    "PlaceholderMapper",
]
