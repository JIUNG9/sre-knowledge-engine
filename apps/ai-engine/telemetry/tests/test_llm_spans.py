"""Tests for telemetry.llm_spans — GenAI semconv compliance."""

from __future__ import annotations

import pytest
from opentelemetry.trace import StatusCode

from telemetry import trace_llm_call
from telemetry.llm_spans import (
    ATTR_OPERATION,
    ATTR_REQUEST_MAX_TOKENS,
    ATTR_REQUEST_MODEL,
    ATTR_REQUEST_TEMPERATURE,
    ATTR_RESPONSE_ID,
    ATTR_RESPONSE_MODEL,
    ATTR_SYSTEM,
    ATTR_USAGE_INPUT_TOKENS,
    ATTR_USAGE_OUTPUT_TOKENS,
)


def test_llm_span_has_genai_semconv_attributes(memory_exporter) -> None:
    """A successful LLM call emits all stable gen_ai.* attributes."""
    with trace_llm_call(
        model="claude-opus-4-7",
        operation="chat",
        max_tokens=4096,
        temperature=0.2,
    ) as llm:
        llm.set_response(
            model="claude-opus-4-7-20260101",
            response_id="msg_01ABCD",
            input_tokens=512,
            output_tokens=128,
            finish_reasons=["end_turn"],
        )

    spans = memory_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]

    assert span.name == "chat claude-opus-4-7"
    attrs = dict(span.attributes or {})
    assert attrs[ATTR_SYSTEM] == "anthropic"
    assert attrs[ATTR_OPERATION] == "chat"
    assert attrs[ATTR_REQUEST_MODEL] == "claude-opus-4-7"
    assert attrs[ATTR_REQUEST_MAX_TOKENS] == 4096
    assert attrs[ATTR_REQUEST_TEMPERATURE] == pytest.approx(0.2)
    assert attrs[ATTR_RESPONSE_MODEL] == "claude-opus-4-7-20260101"
    assert attrs[ATTR_RESPONSE_ID] == "msg_01ABCD"
    assert attrs[ATTR_USAGE_INPUT_TOKENS] == 512
    assert attrs[ATTR_USAGE_OUTPUT_TOKENS] == 128
    assert span.status.status_code == StatusCode.OK


def test_llm_span_system_inference(memory_exporter) -> None:
    """gen_ai.system is inferred from the model name when not given."""
    with trace_llm_call(model="gpt-5-mini", operation="chat"):
        pass
    with trace_llm_call(model="gemini-2-flash", operation="chat"):
        pass
    with trace_llm_call(model="llama-3.1-70b", operation="chat"):
        pass

    spans = memory_exporter.get_finished_spans()
    systems = [dict(s.attributes or {}).get(ATTR_SYSTEM) for s in spans]
    assert systems == ["openai", "google", "meta"]


def test_llm_span_explicit_system_override(memory_exporter) -> None:
    """An explicit system arg overrides model-name inference."""
    with trace_llm_call(
        model="custom-model-x",
        operation="chat",
        system="my-internal-llm",
    ):
        pass
    span = memory_exporter.get_finished_spans()[0]
    assert dict(span.attributes or {})[ATTR_SYSTEM] == "my-internal-llm"


def test_llm_span_records_exception(memory_exporter) -> None:
    """Exceptions raised inside the block are recorded and re-raised."""

    class LLMBoom(Exception):
        pass

    with pytest.raises(LLMBoom):
        with trace_llm_call(model="claude-opus-4-7", operation="chat"):
            raise LLMBoom("rate limited")

    spans = memory_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.status_code == StatusCode.ERROR
    assert any(ev.name == "exception" for ev in span.events)


def test_llm_span_operation_in_name(memory_exporter) -> None:
    """Span name follows '<operation> <model>' convention from GenAI semconv."""
    with trace_llm_call(model="text-embedding-3", operation="embeddings"):
        pass
    span = memory_exporter.get_finished_spans()[0]
    assert span.name == "embeddings text-embedding-3"
