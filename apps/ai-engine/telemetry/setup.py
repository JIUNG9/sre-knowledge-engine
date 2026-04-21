"""OpenTelemetry SDK bootstrap for Aegis.

``setup_telemetry`` is idempotent: calling it twice is harmless. The global
TracerProvider is installed exactly once. Subsequent calls return the same
provider and ignore the new config unless ``force=True`` is passed.

Design notes
------------
* We use a ``TracerProvider`` with a ``Resource`` carrying ``service.name``
  and ``service.version`` so Datadog/Honeycomb/Tempo can route traces.
* The sampler is ``ParentBased(TraceIdRatioBased(sample_ratio))`` so
  downstream services inherit sampling decisions made upstream — the
  recommended pattern for GenAI semantic conventions.
* The OTLP HTTP exporter honors ``OTEL_EXPORTER_OTLP_ENDPOINT`` and
  ``OTEL_EXPORTER_OTLP_HEADERS`` natively, so we pass only the endpoint
  if the user set one explicitly; otherwise we let the exporter read env.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from telemetry.config import TelemetryConfig

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger("aegis.telemetry")

_lock = threading.Lock()
_initialized: bool = False
_provider: "TracerProvider | None" = None
_active_config: TelemetryConfig | None = None


def is_initialized() -> bool:
    """Return True once ``setup_telemetry`` has installed a provider."""
    return _initialized


def get_active_config() -> TelemetryConfig | None:
    """Return the config that produced the current global provider, if any."""
    return _active_config


def setup_telemetry(
    config: TelemetryConfig | None = None,
    *,
    force: bool = False,
) -> "TracerProvider | None":
    """Install the global OTel TracerProvider for Aegis.

    Args:
        config: Telemetry configuration. Defaults to ``TelemetryConfig.from_env()``.
        force: If True, re-install the provider even if one already exists.
            Useful for tests that swap exporters between cases.

    Returns:
        The installed ``TracerProvider``, or ``None`` if telemetry is disabled
        (config.enabled is False).

    This function is safe to call from any thread and from multiple entry
    points (FastAPI startup, CLI, tests).
    """
    global _initialized, _provider, _active_config

    cfg = config or TelemetryConfig.from_env()

    if not cfg.enabled:
        logger.debug("Aegis telemetry disabled (config.enabled=False)")
        _active_config = cfg
        return None

    with _lock:
        if _initialized and not force:
            return _provider

        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor,
                ConsoleSpanExporter,
                SimpleSpanProcessor,
            )
            from opentelemetry.sdk.trace.sampling import (
                ParentBased,
                TraceIdRatioBased,
            )
        except ImportError as exc:  # pragma: no cover - optional dep
            logger.warning(
                "opentelemetry-sdk not installed — telemetry disabled (%s)", exc
            )
            return None

        resource_attrs = {
            "service.name": cfg.service_name,
            "service.version": cfg.service_version,
            **cfg.resource_attributes,
        }
        resource = Resource.create(resource_attrs)

        sampler = ParentBased(TraceIdRatioBased(cfg.sample_ratio))
        provider = TracerProvider(resource=resource, sampler=sampler)

        if cfg.exporter == "console":
            # SimpleSpanProcessor -> synchronous stdout, deterministic for devs.
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        elif cfg.exporter == "otlp":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
            except ImportError as exc:  # pragma: no cover - optional dep
                logger.warning(
                    "OTLP exporter requested but opentelemetry-exporter-otlp "
                    "not installed (%s) — falling back to console",
                    exc,
                )
                provider.add_span_processor(
                    SimpleSpanProcessor(ConsoleSpanExporter())
                )
            else:
                kwargs: dict[str, str] = {}
                if cfg.otlp_endpoint:
                    kwargs["endpoint"] = cfg.otlp_endpoint
                exporter = OTLPSpanExporter(**kwargs)
                provider.add_span_processor(BatchSpanProcessor(exporter))
        elif cfg.exporter == "none":
            # Caller attaches their own processor (tests).
            pass

        trace.set_tracer_provider(provider)
        _provider = provider
        _active_config = cfg
        _initialized = True
        logger.info(
            "Aegis telemetry initialized (exporter=%s, sample_ratio=%.2f)",
            cfg.exporter,
            cfg.sample_ratio,
        )
        return provider


def reset_for_tests() -> None:
    """Reset module-level state. **Tests only.**"""
    global _initialized, _provider, _active_config
    with _lock:
        _initialized = False
        _provider = None
        _active_config = None
