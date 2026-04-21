# Aegis Layer 0.1 — PII Redaction Proxy

`apps/ai-engine/proxy/` is a drop-in wrapper around the official
`anthropic.Anthropic` client. Every outbound prompt is scanned for PII
(emails, IPv4/IPv6, AWS account IDs and access keys, internal hostnames
ending in `.internal`, `.local`, `.corp`, `.intranet`, `.lan`, JWT and
Bearer tokens, PEM blocks), each hit is replaced
with a deterministic per-request placeholder such as `<EMAIL_1>`, and
the value is stashed in a thread-safe in-memory map with a TTL. When
Claude replies, the proxy reverse-substitutes placeholders back to their
original values before handing the response to the caller. Detection is
regex-only out of the box; install the optional `presidio` extra for
NER-assisted person-name and phone-number detection. The proxy is
default-on, fully in-process, and degrades to a pure passthrough when
`PIIProxyConfig(enabled=False)`. Streaming is preserved: text deltas are
restored event-by-event as they arrive from the SDK.

## Basic use

```python
import anthropic
from proxy import AnthropicProxy, PIIProxyConfig

client = AnthropicProxy(anthropic.Anthropic(), PIIProxyConfig())

resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": "User alice.dev@acme-corp.com from 10.0.0.42 hit db01.prod.internal",
    }],
)
print(resp.content[0].text)  # placeholders already un-redacted
```

## With streaming

```python
import anthropic
from proxy import AnthropicProxy, PIIProxyConfig

client = AnthropicProxy(anthropic.Anthropic(), PIIProxyConfig())

stream = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    stream=True,
    messages=[{"role": "user", "content": "summarize 10.0.0.42 activity"}],
)
for event in stream:
    if getattr(event, "delta", None) and getattr(event.delta, "text", None):
        print(event.delta.text, end="", flush=True)
```

## With custom patterns

```python
import anthropic
from proxy import AnthropicProxy, PIIProxyConfig

config = PIIProxyConfig(
    custom_patterns=[r"INC-\d{4}", r"ticket/\w{8}"],
    mapping_ttl_seconds=1800,
)
client = AnthropicProxy(anthropic.Anthropic(), config)

client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[{"role": "user", "content": "investigate INC-0042"}],
)
```

## Running the tests

```bash
cd apps/ai-engine
pytest proxy/tests/
```

## Files

| File | Role |
| --- | --- |
| `__init__.py` | Public API re-exports |
| `config.py` | `PIIProxyConfig` (Pydantic) |
| `detector.py` | Regex + optional Presidio detection |
| `mapper.py` | Thread-safe, TTL-bounded placeholder map |
| `proxy.py` | `AnthropicProxy` client wrapper |
| `tests/` | pytest suite — 43 tests, regex-only fixtures |

Licensed under Apache-2.0. Copyright 2025 June Gu.
