"""OpenTelemetry spans for LLM calls, conforming to GenAI semantic conventions.

Spec: https://opentelemetry.io/docs/specs/semconv/gen-ai/

We emit the stable subset of ``gen_ai.*`` attributes that every supported
backend (Datadog, Honeycomb, Grafana Tempo, SigNoz, Jaeger) understands as
of 2026-04. Attributes intentionally omitted are documented in the module
README so reviewers know they were a deliberate choice, not an oversight.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from opentelemetry.trace import Span

logger = logging.getLogger("aegis.telemetry.llm")

# GenAI semantic convention attribute keys (stable subset).
ATTR_SYSTEM = "gen_ai.system"
ATTR_OPERATION = "gen_ai.operation.name"
ATTR_REQUEST_MODEL = "gen_ai.request.model"
ATTR_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
ATTR_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
ATTR_REQUEST_TOP_P = "gen_ai.request.top_p"
ATTR_RESPONSE_MODEL = "gen_ai.response.model"
ATTR_RESPONSE_ID = "gen_ai.response.id"
ATTR_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
ATTR_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
ATTR_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"


def _infer_system(model: str) -> str:
    """Best-effort mapping from model string to gen_ai.system value."""
    m = model.lower()
    if "claude" in m:
        return "anthropic"
    if m.startswith("gpt") or "openai" in m:
        return "openai"
    if "gemini" in m:
        return "google"
    if "mistral" in m:
        return "mistral"
    if "llama" in m or "gemma" in m:
        return "meta"
    return "unknown"


class LLMSpanHandle:
    """Handle returned by ``trace_llm_call`` for recording response fields.

    Usage:
        with trace_llm_call(model="claude-opus-4", operation="chat") as span:
            span.set_request(max_tokens=4096, temperature=0.2)
            response = client.messages.create(...)
            span.set_response(
                model=response.model,
                response_id=response.id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
    """

    def __init__(self, otel_span: "Span | None") -> None:
        self._span = otel_span

    @property
    def span(self) -> "Span | None":
        return self._span

    def _set(self, key: str, value: Any) -> None:
        if self._span is None or not self._span.is_recording():
            return
        if value is None:
            return
        self._span.set_attribute(key, value)

    def set_request(
        self,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> None:
        self._set(ATTR_REQUEST_MAX_TOKENS, max_tokens)
        self._set(ATTR_REQUEST_TEMPERATURE, temperature)
        self._set(ATTR_REQUEST_TOP_P, top_p)

    def set_response(
        self,
        *,
        model: str | None = None,
        response_id: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        finish_reasons: list[str] | None = None,
    ) -> None:
        self._set(ATTR_RESPONSE_MODEL, model)
        self._set(ATTR_RESPONSE_ID, response_id)
        self._set(ATTR_USAGE_INPUT_TOKENS, input_tokens)
        self._set(ATTR_USAGE_OUTPUT_TOKENS, output_tokens)
        if finish_reasons:
            self._set(ATTR_RESPONSE_FINISH_REASONS, tuple(finish_reasons))

    def set_attribute(self, key: str, value: Any) -> None:
        """Escape hatch for vendor-specific or future attributes."""
        self._set(key, value)


@contextmanager
def trace_llm_call(
    model: str,
    operation: str,
    *,
    system: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Iterator[LLMSpanHandle]:
    """Create an OTel span for one LLM call, following GenAI semconv.

    Args:
        model: Requested model id (e.g. ``"claude-opus-4-7"``).
        operation: GenAI operation name, per spec. Common values:
            ``"chat"``, ``"text_completion"``, ``"embeddings"``.
        system: Override ``gen_ai.system``. If None, inferred from ``model``.
        max_tokens: Optional request-side attribute, set upfront.
        temperature: Optional request-side attribute, set upfront.

    Yields:
        ``LLMSpanHandle`` — call ``set_response(...)`` with usage data once
        the LLM reply arrives.

    On exception, records it on the span and marks status=ERROR before
    re-raising. On success with zero info from caller, still emits a valid
    span containing the request-side attributes.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind, Status, StatusCode
    except ImportError:  # pragma: no cover
        # OTel absent: give caller a no-op handle, zero overhead.
        yield LLMSpanHandle(None)
        return

    tracer = trace.get_tracer("aegis.telemetry.llm", "0.4.0")
    span_name = f"{operation} {model}"
    system_value = system or _infer_system(model)

    with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
        handle = LLMSpanHandle(span)
        handle.set_attribute(ATTR_SYSTEM, system_value)
        handle.set_attribute(ATTR_OPERATION, operation)
        handle.set_attribute(ATTR_REQUEST_MODEL, model)
        handle.set_request(max_tokens=max_tokens, temperature=temperature)
        try:
            yield handle
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        else:
            # Only mark OK if caller didn't set an error state explicitly.
            if span.is_recording() and span.status.status_code != StatusCode.ERROR:
                span.set_status(Status(StatusCode.OK))
