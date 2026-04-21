"""Shared test fixtures: attach an in-memory span exporter to the TracerProvider.

OTel refuses to re-install the global TracerProvider once set, so the
strategy is: install a real TracerProvider ONCE for the test session, and
give each test its own InMemorySpanExporter attached as a span processor.
Each test clears the exporter at teardown.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure 'telemetry' is importable when running pytest from the ai-engine dir.
_AI_ENGINE = Path(__file__).resolve().parents[2]
if str(_AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINE))

from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.resources import Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: E402
    InMemorySpanExporter,
)

from telemetry import reset_for_tests  # noqa: E402

_TEST_PROVIDER: TracerProvider | None = None


def _get_or_install_provider() -> TracerProvider:
    global _TEST_PROVIDER
    if _TEST_PROVIDER is None:
        provider = TracerProvider(
            resource=Resource.create(
                {"service.name": "aegis-test", "service.version": "0.4.0"}
            )
        )
        trace.set_tracer_provider(provider)
        _TEST_PROVIDER = provider
    return _TEST_PROVIDER


@pytest.fixture()
def memory_exporter() -> InMemorySpanExporter:
    """Attach a fresh InMemorySpanExporter to the session TracerProvider.

    We use SimpleSpanProcessor (synchronous) so spans are visible
    immediately on block exit, no flush needed.
    """
    reset_for_tests()
    provider = _get_or_install_provider()
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    try:
        yield exporter
    finally:
        processor.shutdown()
        exporter.clear()
        reset_for_tests()
