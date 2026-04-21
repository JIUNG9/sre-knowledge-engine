# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0.
"""Integration tests for :class:`AnthropicProxy` using a fake SDK client.

We intentionally do not hit the real Anthropic API. The tests build a
minimal stand-in that mirrors the structural contract the proxy relies on
(``.messages.create()`` returning an object with a ``content`` list of
blocks that expose a mutable ``.text`` attribute, plus an iterable stream
mode).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


from proxy import AnthropicProxy, PIIProxyConfig


# --------------------------------------------------------------------------- #
# Fake SDK doubles.
# --------------------------------------------------------------------------- #
@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeMessage:
    content: list[_FakeTextBlock] = field(default_factory=list)
    id: str = "msg_test"
    role: str = "assistant"
    stop_reason: str | None = "end_turn"


@dataclass
class _FakeDelta:
    text: str
    type: str = "text_delta"


@dataclass
class _FakeStreamEvent:
    delta: _FakeDelta
    type: str = "content_block_delta"


class _FakeMessages:
    def __init__(self) -> None:
        self.received_kwargs: dict[str, Any] | None = None
        self.reply: _FakeMessage | None = None
        self.stream_events: list[Any] = []

    def create(self, **kwargs: Any) -> Any:
        self.received_kwargs = kwargs
        if kwargs.get("stream"):
            return iter(self.stream_events)
        return self.reply


class _FakeAnthropic:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


# --------------------------------------------------------------------------- #
# Tests.
# --------------------------------------------------------------------------- #
def test_outbound_message_is_redacted() -> None:
    fake = _FakeAnthropic()
    fake.messages.reply = _FakeMessage(content=[_FakeTextBlock(text="acknowledged")])
    proxy = AnthropicProxy(fake, PIIProxyConfig())

    proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        system="You are an SRE assistant investigating db01.prod.internal",
        messages=[
            {
                "role": "user",
                "content": "User alice.dev@acme-corp.com from 10.0.0.42 hit acct 123456789012",
            }
        ],
    )

    sent = fake.messages.received_kwargs
    assert sent is not None
    assert "db01.prod.internal" not in sent["system"]
    body = sent["messages"][0]["content"]
    assert "alice.dev@acme-corp.com" not in body
    assert "10.0.0.42" not in body
    assert "123456789012" not in body
    # Placeholders are present in the redacted payload.
    assert "<EMAIL_1>" in body
    assert "<IPV4_1>" in body
    assert "<AWS_ACCOUNT_1>" in body


def test_response_is_restored_end_to_end() -> None:
    fake = _FakeAnthropic()
    # Simulate Claude parroting back the placeholders it received.
    fake.messages.reply = _FakeMessage(
        content=[
            _FakeTextBlock(
                text="Incident summary: <EMAIL_1> logged in from <IPV4_1> on host <HOST_1>."
            )
        ]
    )
    proxy = AnthropicProxy(fake, PIIProxyConfig())

    resp = proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        messages=[
            {
                "role": "user",
                "content": (
                    "Alert: alice.dev@acme-corp.com logged in from 10.0.0.42 "
                    "on host db01.prod.internal"
                ),
            }
        ],
    )

    assert "alice.dev@acme-corp.com" in resp.content[0].text
    assert "10.0.0.42" in resp.content[0].text
    assert "db01.prod.internal" in resp.content[0].text
    assert "<EMAIL_1>" not in resp.content[0].text


def test_passthrough_when_disabled() -> None:
    fake = _FakeAnthropic()
    fake.messages.reply = _FakeMessage(content=[_FakeTextBlock(text="hi")])
    proxy = AnthropicProxy(fake, PIIProxyConfig(enabled=False))

    original = "contact alice.dev@acme-corp.com"
    proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        messages=[{"role": "user", "content": original}],
    )
    sent = fake.messages.received_kwargs
    assert sent is not None
    assert sent["messages"][0]["content"] == original


def test_caller_input_is_not_mutated() -> None:
    fake = _FakeAnthropic()
    fake.messages.reply = _FakeMessage(content=[_FakeTextBlock(text="ok")])
    proxy = AnthropicProxy(fake, PIIProxyConfig())

    original_msgs = [
        {"role": "user", "content": "email alice.dev@acme-corp.com"}
    ]
    proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        messages=original_msgs,
    )
    # Caller's list must be untouched.
    assert original_msgs[0]["content"] == "email alice.dev@acme-corp.com"


def test_streaming_restores_deltas() -> None:
    fake = _FakeAnthropic()
    fake.messages.stream_events = [
        _FakeStreamEvent(delta=_FakeDelta(text="user ")),
        _FakeStreamEvent(delta=_FakeDelta(text="<EMAIL_1>")),
        _FakeStreamEvent(delta=_FakeDelta(text=" from <IPV4_1>")),
    ]
    proxy = AnthropicProxy(fake, PIIProxyConfig())

    stream = proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        stream=True,
        messages=[
            {
                "role": "user",
                "content": "user alice.dev@acme-corp.com from 10.0.0.42",
            }
        ],
    )
    collected: list[str] = [e.delta.text for e in stream]
    assert "".join(collected) == "user alice.dev@acme-corp.com from 10.0.0.42"


def test_content_list_text_blocks_are_redacted() -> None:
    fake = _FakeAnthropic()
    fake.messages.reply = _FakeMessage(content=[_FakeTextBlock(text="ok")])
    proxy = AnthropicProxy(fake, PIIProxyConfig())

    proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "from 10.0.0.42"},
                    {"type": "text", "text": "to 10.0.0.99"},
                ],
            }
        ],
    )
    sent = fake.messages.received_kwargs
    assert sent is not None
    blocks = sent["messages"][0]["content"]
    assert blocks[0]["text"] == "from <IPV4_1>"
    assert blocks[1]["text"] == "to <IPV4_2>"


def test_custom_patterns_redacted() -> None:
    fake = _FakeAnthropic()
    fake.messages.reply = _FakeMessage(content=[_FakeTextBlock(text="ack")])
    config = PIIProxyConfig(custom_patterns=[r"INC-\d{4}"])
    proxy = AnthropicProxy(fake, config)

    proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        messages=[{"role": "user", "content": "See INC-0042"}],
    )
    sent = fake.messages.received_kwargs
    assert sent is not None
    assert "INC-0042" not in sent["messages"][0]["content"]
    assert "<CUSTOM_1>" in sent["messages"][0]["content"]


def test_scope_dropped_after_call_when_not_preserving() -> None:
    fake = _FakeAnthropic()
    fake.messages.reply = _FakeMessage(content=[_FakeTextBlock(text="ok")])
    proxy = AnthropicProxy(
        fake, PIIProxyConfig(preserve_mapping=False)
    )
    proxy.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        messages=[{"role": "user", "content": "10.0.0.1"}],
    )
    # No scope should be alive.
    assert proxy.mapper._scopes == {}  # noqa: SLF001 - internal, but clear intent


def test_fallthrough_to_underlying_client() -> None:
    fake = _FakeAnthropic()
    fake.api_key = "sk-test"  # type: ignore[attr-defined]
    proxy = AnthropicProxy(fake, PIIProxyConfig())
    # Attribute that exists on the wrapped client but not on the proxy itself.
    assert proxy.api_key == "sk-test"
