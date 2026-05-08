"""Tests for :mod:`invalidation.metrics`.

Strategy: register a real :class:`MeterProvider` with an
:class:`InMemoryMetricReader`, then run engine code paths and assert
the recorded counters carry the expected names + values + attributes.
The provider is process-global, so we install it in a fixture and
let it stay registered for the test session — the SDK's idempotency
keeps subsequent registrations safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from invalidation.dependency_index import DependencyIndex
from invalidation.engine import InvalidationEngine
from state_subscription.models import StateChangeEvent
from wiki.synthesizer import WikiPage


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def metric_reader() -> InMemoryMetricReader:
    """Install an InMemoryMetricReader as the global metrics backend.

    Module-scoped because the SDK only honors the FIRST set_meter_provider
    call (subsequent calls log a warning and are ignored). All tests in
    this module share the reader; assertions slice by counter name.
    """
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return reader


def _counter_total(reader: InMemoryMetricReader, name: str) -> float:
    """Sum every data point for ``name`` across all metric attribute sets."""
    data = reader.get_metrics_data()
    if data is None:
        return 0.0
    total = 0.0
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name != name:
                    continue
                for point in metric.data.data_points:
                    total += point.value
    return total


async def test_handle_event_increments_records_and_pages(
    metric_reader: InMemoryMetricReader,
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """One non-shadow event with two dependents must increment the
    records-total counter by 1 and the pages-marked counter by 2."""
    # NOTE: meters are cached at module import time. Re-importing is the
    # simplest way to make sure they bind to the now-installed provider.
    import importlib
    import invalidation.metrics as m

    importlib.reload(m)
    # Reload anything that captured the previous counters by reference.
    import invalidation.engine as e

    importlib.reload(e)

    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = e.InvalidationEngine(vault_root=tmp_vault, index=index)

    records_before = _counter_total(
        metric_reader, "aegis_invalidation_records_total"
    )
    pages_before = _counter_total(
        metric_reader, "aegis_invalidation_pages_marked_total"
    )

    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )

    # Force the reader to collect; otherwise pending writes won't show.
    metric_reader.collect()

    records_after = _counter_total(
        metric_reader, "aegis_invalidation_records_total"
    )
    pages_after = _counter_total(
        metric_reader, "aegis_invalidation_pages_marked_total"
    )

    assert records_after - records_before == 1
    # auth-service + scaling-runbook = 2 pages
    assert pages_after - pages_before == 2


async def test_shadow_mode_records_but_does_not_count_pages_marked(
    metric_reader: InMemoryMetricReader,
    tmp_vault: Path,
    sample_pages: list[WikiPage],
) -> None:
    """Shadow mode increments the audit-record counter but not
    pages-marked — the engine logs but doesn't mutate."""
    import importlib
    import invalidation.metrics as m

    importlib.reload(m)
    import invalidation.engine as e

    importlib.reload(e)

    index = DependencyIndex()
    await index.rebuild(sample_pages)
    engine = e.InvalidationEngine(
        vault_root=tmp_vault, index=index, shadow_mode=True
    )

    records_before = _counter_total(
        metric_reader, "aegis_invalidation_records_total"
    )
    pages_before = _counter_total(
        metric_reader, "aegis_invalidation_pages_marked_total"
    )

    await engine.handle_event(
        StateChangeEvent(
            artifact_kind="k8s",
            artifact_id="k8s:Deployment:default/auth-service:spec.replicas",
            old_value="3",
            new_value="5",
            source="k8s://default/auth-service",
        )
    )
    metric_reader.collect()

    records_after = _counter_total(
        metric_reader, "aegis_invalidation_records_total"
    )
    pages_after = _counter_total(
        metric_reader, "aegis_invalidation_pages_marked_total"
    )

    assert records_after - records_before == 1
    assert pages_after - pages_before == 0
