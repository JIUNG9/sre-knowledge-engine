"""OpenTelemetry metrics for Layer 1.5 + 1.6.

Per design doc §4: consumers expose events/errors/last-event-age, and
the invalidation engine exposes per-record / per-page / fanout-truncate
counters. The SDK is initialized elsewhere (telemetry/setup.py +
OTLP collector); this module just declares the instruments.

Why OTel rather than prometheus_client direct: Aegis already ships
opentelemetry-{api,sdk} for tracing, and a deploy-side OTel collector
(or the OTLP HTTP exporter) routes to whichever metrics backend the
operator runs. One pipeline, one set of attributes, one collector.
The metric NAMES still match the design doc (Prometheus convention)
because the collector pipeline preserves them.

When no MeterProvider is registered, every call below is a no-op —
import + use is safe in CI / unit tests / cold starts that haven't
called ``setup_telemetry()``.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from opentelemetry import metrics

# One named meter for every Layer 1.5/1.6 instrument. The version
# string is informational; bump it in major refactors so dashboards
# can group by deploy.
_meter = metrics.get_meter("aegis.invalidation", "1.0.0")

# -- Consumer (Layer 1.5) -------------------------------------------- #

CONSUMER_EVENTS_TOTAL = _meter.create_counter(
    name="aegis_consumer_events_total",
    unit="1",
    description=(
        "Count of StateChangeEvent records emitted by a consumer. "
        "Attributes: consumer (k8s|terraform|argocd|...), "
        "kind (Deployment|StatefulSet|...)."
    ),
)

CONSUMER_ERRORS_TOTAL = _meter.create_counter(
    name="aegis_consumer_errors_total",
    unit="1",
    description=(
        "Count of consumer-side errors. Attributes: "
        "consumer, error_type (watch_disconnect|parse|init|...)."
    ),
)

# Last-event timestamp per consumer, observed via callback. Operators
# alert on `aegis_consumer_last_event_seconds > N` to catch a silent
# watch loop. Stored as a wall-clock seconds-since-epoch; consumer
# code calls _last_event_at[consumer_name] = time.time() on every yield.
_last_event_at: dict[str, float] = {}


def _observe_last_event(
    options: metrics.CallbackOptions,
) -> Iterable[metrics.Observation]:
    """ObservableGauge callback: emit one observation per known consumer."""
    return [
        metrics.Observation(value=ts, attributes={"consumer": name})
        for name, ts in _last_event_at.items()
    ]


CONSUMER_LAST_EVENT_SECONDS = _meter.create_observable_gauge(
    name="aegis_consumer_last_event_seconds",
    unit="s",
    description=(
        "Wall-clock seconds since epoch of the most recent event yielded "
        "by each consumer. Operators alert on (now() - value) > threshold "
        "to catch silently-broken watch loops."
    ),
    callbacks=[_observe_last_event],
)


def record_consumer_event(consumer: str, kind: str | None = None) -> None:
    """Increment the consumer event counter and bump last-event-at."""
    attributes = {"consumer": consumer}
    if kind is not None:
        attributes["kind"] = kind
    CONSUMER_EVENTS_TOTAL.add(1, attributes)
    _last_event_at[consumer] = time.time()


def record_consumer_error(consumer: str, error_type: str) -> None:
    """Increment the consumer error counter."""
    CONSUMER_ERRORS_TOTAL.add(
        1, {"consumer": consumer, "error_type": error_type}
    )


# -- Engine (Layer 1.6) ---------------------------------------------- #

INVALIDATION_RECORDS_TOTAL = _meter.create_counter(
    name="aegis_invalidation_records_total",
    unit="1",
    description=(
        "Count of InvalidationRecord audit entries written. Attributes: "
        "shadow (true|false), reason (value_change|first_observation|...)."
    ),
)

INVALIDATION_PAGES_MARKED_TOTAL = _meter.create_counter(
    name="aegis_invalidation_pages_marked_total",
    unit="1",
    description=(
        "Count of wiki pages flipped to pending_revalidation. Equal to "
        "the sum of len(record.affected_slugs) over all non-shadow records. "
        "Used to size the resynth-queue consumer's expected throughput."
    ),
)

INVALIDATION_FANOUT_TRUNCATED_TOTAL = _meter.create_counter(
    name="aegis_invalidation_fanout_truncated_total",
    unit="1",
    description=(
        "Count of events whose fanout exceeded fanout_cap and was truncated. "
        "When this counter increments, the daily reconciliation pass is the "
        "safety net that picks up the dropped tail."
    ),
)

INVALIDATION_CONFLICTS_TOTAL = _meter.create_counter(
    name="aegis_invalidation_conflicts_total",
    unit="1",
    description=(
        "Count of concurrent-edit conflicts detected: a human edited the "
        "page after the engine's last write, so the engine skipped its "
        "rewrite. Operator-edit-wins is the design choice (§7); this counter "
        "lets you spot a pathologically chatty page."
    ),
)


def record_invalidation(
    *,
    shadow: bool,
    reason: str,
    pages_marked: int,
    truncated: bool,
) -> None:
    """One-call helper: bump every engine counter for one handle_event."""
    attrs_record = {"shadow": str(shadow).lower(), "reason": reason}
    INVALIDATION_RECORDS_TOTAL.add(1, attrs_record)
    if pages_marked:
        INVALIDATION_PAGES_MARKED_TOTAL.add(
            pages_marked, {"shadow": str(shadow).lower()}
        )
    if truncated:
        INVALIDATION_FANOUT_TRUNCATED_TOTAL.add(1)


def record_conflict() -> None:
    """Concurrent-edit conflict counter."""
    INVALIDATION_CONFLICTS_TOTAL.add(1)
