"""Configuration for Aegis OpenTelemetry GenAI tracing.

The TelemetryConfig is the single source of truth for how traces are emitted.
It is intentionally small: Aegis only needs to know (1) whether tracing is on,
(2) where to ship spans, and (3) what sample ratio to apply.

Environment variables honored:
    OTEL_EXPORTER_OTLP_ENDPOINT   — overrides ``otlp_endpoint`` if set
    OTEL_EXPORTER_OTLP_HEADERS    — consumed by the OTLP HTTP exporter
    AEGIS_TELEMETRY_ENABLED       — "0"/"false" disables telemetry globally
    AEGIS_TELEMETRY_EXPORTER      — "console" | "otlp" | "none"
    AEGIS_TELEMETRY_SAMPLE_RATIO  — float in [0.0, 1.0]
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

ExporterKind = Literal["console", "otlp", "none"]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class TelemetryConfig:
    """Aegis telemetry configuration.

    Attributes:
        enabled: When False, ``setup_telemetry`` becomes a no-op and the
            span context managers yield a non-recording span (zero overhead).
        exporter: Which span exporter to register.
            ``"console"`` prints JSON to stdout (solo-developer default).
            ``"otlp"`` ships to an OTLP/HTTP collector (Honeycomb, Datadog,
            Jaeger, Grafana Tempo, SigNoz).
            ``"none"`` registers no exporter — useful for tests that attach
            their own in-memory exporter.
        otlp_endpoint: OTLP collector URL. Falls back to the standard
            ``OTEL_EXPORTER_OTLP_ENDPOINT`` env var.
        sample_ratio: Trace sampling ratio in [0.0, 1.0]. 1.0 = record all.
        service_name: ``service.name`` resource attribute.
        service_version: ``service.version`` resource attribute.
    """

    enabled: bool = True
    exporter: ExporterKind = "console"
    otlp_endpoint: str | None = None
    sample_ratio: float = 1.0
    service_name: str = "aegis"
    service_version: str = "0.4.0"
    resource_attributes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.sample_ratio <= 1.0:
            raise ValueError(
                f"sample_ratio must be in [0.0, 1.0], got {self.sample_ratio}"
            )
        if self.exporter not in ("console", "otlp", "none"):
            raise ValueError(
                f"exporter must be 'console', 'otlp', or 'none', got {self.exporter!r}"
            )

    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        """Build a config from environment variables.

        Precedence: AEGIS_TELEMETRY_EXPORTER overrides auto-detection.
        If OTEL_EXPORTER_OTLP_ENDPOINT is set and no explicit exporter
        is configured, we promote to ``otlp``.
        """
        enabled = _env_bool("AEGIS_TELEMETRY_ENABLED", True)
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None

        raw_exporter = os.environ.get("AEGIS_TELEMETRY_EXPORTER")
        if raw_exporter:
            exporter: ExporterKind = raw_exporter.strip().lower()  # type: ignore[assignment]
        elif otlp_endpoint:
            exporter = "otlp"
        else:
            exporter = "console"

        sample_ratio = _env_float("AEGIS_TELEMETRY_SAMPLE_RATIO", 1.0)

        return cls(
            enabled=enabled,
            exporter=exporter,
            otlp_endpoint=otlp_endpoint,
            sample_ratio=sample_ratio,
        )
