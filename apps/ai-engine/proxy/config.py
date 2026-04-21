# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""Configuration for the Aegis PII redaction proxy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PIIProxyConfig(BaseModel):
    """Runtime configuration for :class:`AnthropicProxy`.

    Attributes:
        enabled: If ``False`` the proxy becomes a pure passthrough — no
            detection or substitution is performed. Defaults to ``True``.
        provider: Detection backend. ``"regex"`` uses only the built-in
            regex patterns. ``"presidio"`` uses Microsoft Presidio exclusively
            (and raises if ``presidio-analyzer`` is not installed). ``"hybrid"``
            (default) prefers Presidio when available and merges regex hits.
        preserve_mapping: When ``True`` (default) the proxy keeps the
            placeholder->value map alive for ``mapping_ttl_seconds`` so
            responses can be reverse-substituted. When ``False`` mappings are
            dropped after the request completes (one-way redaction).
        mapping_ttl_seconds: Time-to-live for each request scope's mapping
            store. Defaults to ``3600``.
        custom_patterns: Additional regular expressions (as strings) that
            should also be redacted. Patterns are compiled with ``re.MULTILINE``
            and each match is mapped to a ``<CUSTOM_n>`` placeholder.
    """

    enabled: bool = True
    provider: Literal["presidio", "regex", "hybrid"] = "hybrid"
    preserve_mapping: bool = True
    mapping_ttl_seconds: int = 3600
    custom_patterns: list[str] = Field(default_factory=list)

    def is_passthrough(self) -> bool:
        """Return ``True`` when the proxy should not alter payloads."""
        return not self.enabled
