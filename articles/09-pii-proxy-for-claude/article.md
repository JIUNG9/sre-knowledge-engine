# I Built a PII-Redacting Proxy for Claude — Because My SRE Agent Almost Leaked Production Data to Anthropic

*An AI agent that reads your prod telemetry is one HTTPS call away from being a compliance incident. Here's the ~400 lines of Python I added between my agent and `api.anthropic.com`.*

---

I run an open-source AI SRE platform called [Aegis](https://github.com/JIUNG9/aegis). It reads SigNoz logs, Confluence runbooks, AWS descriptions, and feeds the relevant context into Claude so the model can reason about incidents. Layer 1 ships an LLM-backed wiki. Layer 2 wires in SigNoz. Layer 3 is the Claude "Control Tower" that stitches everything together.

The day I started wiring Layer 3, I looked at my outbound HTTP traffic and saw this:

```
POST https://api.anthropic.com/v1/messages
Content-Type: application/json

{
  "model": "claude-opus-4-7",
  "system": "You are an SRE analyst...",
  "messages": [
    {"role": "user", "content": "Investigate this alert.\n\n2026-04-18 09:13:42 ERROR
      user=kim.jiho@acme-corp.example ip=203.0.113.42 host=prod-db-01.example.internal
      db=acme_orders_prod msg=\"failed login after 5 attempts\""}
  ]
}
```

That is a real internal hostname, a real coworker's email, a real production database name, and a real source IP leaving my laptop in Seoul and ending up on a server in the United States — because my helpful AI agent fetched a real log line and shoved it into the prompt.

Nothing had been pushed to GitHub. The repo was clean. The vault wasn't committed yet. But the data *had* crossed a national border. Every time the agent ran.

This article is about the ~400-line proxy I wrote to stop that, and why it ships *inside* Aegis — not as a thing each user is supposed to remember — so any engineer who clones the repo gets the protection automatically.

> **Repo:** [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
> **Module:** `apps/ai-engine/proxy/`

---

## The problem nobody writes about

Most LLM-agent tutorials skip deployment entirely. The ones that do mention safety say something like:

> "Remember to sanitize sensitive data before sending prompts to the LLM."

That's not a design. That's a prayer. It treats the human operator as the last line of defense — which worked fine when "the LLM" was a chat window you pasted into. It does not work when "the LLM" is an autonomous loop that pulls data from ten sources and fires off API calls on its own.

The structural problem is:

1. Your agent reads **real production telemetry** — that's literally its job.
2. That telemetry contains **real PII and secrets** — hostnames, emails, IPs, account IDs, connection strings.
3. The agent decides **on its own** what context to include in each prompt.
4. Every prompt goes to a **third-party server**, often in a different jurisdiction.

Nothing in that chain involves a human reviewing what gets sent. The "sanitize before you share" rule applied to push-to-GitHub, where there is an obvious checkpoint (the `git push`). There is no equivalent checkpoint between your agent and the LLM API.

Here is the checkpoint I added.

---

## The architecture: a redacting reverse proxy

The mental model is simple — stick a proxy between the agent and Anthropic, scrub PII on the way out, put it back on the way in.

```
  ┌──────────┐      ┌─────────────────┐      ┌──────────────────┐
  │          │      │  PII Proxy      │      │                  │
  │  Aegis   │ ───▶ │  - detect       │ ───▶ │  api.anthropic   │
  │  Agent   │      │  - replace      │      │  .com            │
  │          │ ◀─── │  - reverse-map  │ ◀─── │                  │
  └──────────┘      └─────────────────┘      └──────────────────┘
                          │
                          ▼
                    per-request
                   mapping table
                  (in-memory, TTL)
```

Four moving parts:

1. **Detector** — scans every outbound message for PII and secrets. Regex for the obvious stuff, optionally Microsoft Presidio for the harder stuff (names, organization-specific patterns).
2. **Mapper** — deterministic placeholder generator. `kim.jiho@acme-corp.example` becomes `<USER_1>`. Same input in the same request gets the same placeholder, so downstream reasoning still works. Different requests get independent mappings, so nothing leaks across.
3. **Proxy** — a thin wrapper around `anthropic.Anthropic` that runs detector + mapper before `messages.create(...)` and reverses the substitutions on the response.
4. **Config** — Pydantic settings. On by default, `enabled=False` gives you a passthrough.

That's it. No magic. The whole module is around 400 lines including tests.

---

## What the detector catches

Here is the regex layer, trimmed to the shape (real implementation has boundary anchors and a few exceptions):

```python
# apps/ai-engine/proxy/detector.py

PATTERNS = {
    "email":            r"[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "ipv4":             r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "aws_account_id":   r"\b\d{12}\b",
    "aws_access_key":   r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "internal_host":    r"\b[\w-]+\.(?:internal|local|corp|intranet)\b",
    "jwt":              r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
    "bearer":           r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*",
    "pem_block":        r"-----BEGIN [A-Z ]+-----[\s\S]+?-----END [A-Z ]+-----",
}
```

Optional second layer: if `presidio-analyzer` is installed, the detector hands the text to Presidio for ML-backed recognition of person names, organizations, medical terms, and so on. For a solo operator this is often overkill. For a team shipping Aegis at a hospital it is the difference between "you can deploy this" and "you cannot deploy this." Both paths live behind the same interface, so you flip `provider="hybrid"` in config and it works.

The detector emits a list of **spans** — `(start, end, category, original_text)`. No mutation yet. That's the mapper's job.

---

## What the mapper does with those spans

Two rules:

1. **Deterministic within a request.** If `kim.jiho@acme-corp.example` appears three times in the same prompt, all three become `<USER_1>`. Claude can still reason about "this user did X and then Y and then Z" because the placeholder is stable.
2. **Independent across requests.** If two different users investigate two different incidents, their `<USER_1>`s refer to different people. This is enforced by scoping the map to a per-request context, not a singleton.

```python
# apps/ai-engine/proxy/mapper.py  (sketch)

class RedactionMap:
    def __init__(self, ttl_seconds: int = 3600):
        self._map: dict[str, str] = {}           # placeholder → original
        self._reverse: dict[str, str] = {}       # original → placeholder
        self._counters: dict[str, int] = defaultdict(int)
        self._expires_at = time.time() + ttl_seconds

    def placeholder_for(self, original: str, category: str) -> str:
        if original in self._reverse:
            return self._reverse[original]
        self._counters[category] += 1
        placeholder = f"<{category.upper()}_{self._counters[category]}>"
        self._map[placeholder] = original
        self._reverse[original] = placeholder
        return placeholder

    def reverse(self, text: str) -> str:
        for placeholder, original in self._map.items():
            text = text.replace(placeholder, original)
        return text
```

The `reverse` method is how your eyes — and only your eyes — see the real hostnames in the answer Claude gives you. The placeholder left the laptop. The real name never did.

---

## The proxy itself

The wrapper is the boring part, and that is the point:

```python
# apps/ai-engine/proxy/proxy.py  (sketch)

class AnthropicProxy:
    def __init__(self, inner: anthropic.Anthropic, config: PIIProxyConfig):
        self._inner = inner
        self._config = config
        self._detector = Detector(config)

    def messages_create(self, *, system=None, messages, **kwargs):
        if not self._config.enabled:
            return self._inner.messages.create(system=system, messages=messages, **kwargs)

        redaction = RedactionMap(ttl_seconds=self._config.mapping_ttl_seconds)
        redacted_system, redacted_messages = self._detector.redact(
            system=system, messages=messages, mapping=redaction
        )

        response = self._inner.messages.create(
            system=redacted_system, messages=redacted_messages, **kwargs
        )

        # Reverse-substitute placeholders in the response content
        return _apply_reverse(response, redaction)
```

If `enabled=False`, it is a direct passthrough — zero runtime cost, zero behavioral difference from the bare Anthropic client. If enabled, every outbound payload is scanned, every PII span is swapped for a placeholder, and the response content is post-processed to restore real names before your agent sees it.

Streaming is supported because the reverse substitution is applied per-chunk as the response comes back. Tool use (the `tool_use` content blocks Anthropic returns) is handled the same way — placeholders in the tool arguments get restored before you dispatch the tool call.

---

## Wiring it in — one line of change

Here's what a user of Aegis has to do to turn this on:

```python
# Before:
from anthropic import Anthropic
client = Anthropic()

# After:
from anthropic import Anthropic
from aegis.proxy import AnthropicProxy, PIIProxyConfig

client = AnthropicProxy(Anthropic(), PIIProxyConfig())  # default: enabled
```

That's it. Every call site that used `client.messages.create(...)` continues to work. The agent does not know the proxy exists. The user does not need to remember to sanitize anything — the proxy handles every call, every time.

**This is the whole point.** Safety is a shipped feature, not a user discipline. The rule I had in my head — "June should sanitize before sending" — became a line of code. Any engineer who clones Aegis gets the same protection for free, with no docs to read, no checklist to follow.

---

## Why this matters for Korean law

On April 15, 2026, the amended **Personal Information Protection Act (PIPA)** came into force in Korea. Two bits of the amendment are directly relevant to anyone running an AI agent that touches production data:

1. **Cross-border data transfers** now require explicit consent architecture. Silently sending a log line containing a customer email to a US server is the pattern PIPC has been prosecuting since the DeepSeek ruling.
2. **CEO personal liability** attaches to violations, with fines up to 10% of turnover.

That changes the calculus of "move fast and break things" for any Korean-headquartered org. The PII proxy plus the local-LLM router (Layer 0.4 in Aegis) together give a deployer a defensible position: *"Real prod data never left the country. Only sanitized placeholders crossed the border, and we have OTel traces proving it."*

For a regulated organization, the proxy is not a nice-to-have. It is the difference between "Aegis is deployable under PIPA" and "Aegis is a lawsuit waiting to happen."

This is also why it ships inside the repo, not as a recipe on the wiki. A recipe gets skipped. A hard dependency in `apps/ai-engine/main.py` does not.

---

## Threat model — what this does and does not catch

Let me be specific so nobody thinks this is a silver bullet.

**What the proxy catches well:**
- Structured PII (emails, IPs, AWS IDs, well-formed secrets)
- Hostnames matching your internal-domain patterns
- Secrets that follow recognizable formats (AKIA keys, JWTs, PEM blocks)
- Anything your `custom_patterns` config adds

**What it catches with Presidio enabled:**
- Person names in natural-language text
- Organization names and locations
- Medical terms, credit card numbers (if you need them)

**What it does NOT catch:**
- Novel secret formats your regexes do not know about (rotate your patterns when you rotate your secrets)
- PII embedded in free-text prose without any marker ("the engineer who was oncall last Tuesday")
- Business-sensitive context that is not PII but is still confidential (pricing, org charts)
- Data that the agent *describes* rather than *quotes verbatim*

Those last two are real limitations. If your agent summarizes a confidential document in plain English, the summary may leak intent even if no literal PII string appears. The proxy cannot help with that. Honey tokens (Layer 0.6) and OTel GenAI audit traces (Layer 0.5) cover a different angle of the same problem, and together with the proxy they form a defense-in-depth posture rather than a single silver bullet.

---

## Performance cost

The detector runs in O(n) with respect to prompt size. In practice on prompts up to 50 KB I measured **~4 ms** of added latency on an M2 MacBook, which is well under the network round-trip to Anthropic's API. The mapping table is an in-memory dict that disappears at the end of the request scope, so memory overhead is bounded by the size of a single prompt's PII set — typically a few dozen spans per incident.

If you enable Presidio, expect latency to jump to **~30–80 ms** depending on language model and prompt size. Worth it for a regulated deployment, overkill for a homelab demo. The config lets you pick.

---

## What you do with it

Clone the repo, install, run:

```bash
git clone https://github.com/JIUNG9/aegis
cd aegis
pip install -e "apps/ai-engine[proxy]"
```

Hook it into your existing Claude usage:

```python
from anthropic import Anthropic
from aegis.proxy import AnthropicProxy, PIIProxyConfig

client = AnthropicProxy(
    Anthropic(),
    PIIProxyConfig(
        enabled=True,
        provider="hybrid",              # regex + presidio if installed
        mapping_ttl_seconds=3600,
        custom_patterns=[
            r"\bprod-[a-z0-9-]+\.mycorp\.internal\b",  # your hostnames
        ],
    ),
)

# Use exactly like anthropic.Anthropic — proxy is transparent.
resp = client.messages.create(
    model="claude-opus-4-7",
    system="You are an SRE analyst.",
    messages=[{"role": "user", "content": "Investigate the alert I just fetched from SigNoz."}],
    max_tokens=1024,
)
```

The first time you run a prompt with real data through it, check your outbound HTTPS traffic with `mitmproxy` or similar. You should see `<USER_1>`, `<HOST_1>`, `<IP_1>` in the payload — not the original strings. If you see the originals, file an issue on the repo and I will fix it.

---

## What's next in the series

This is Article #9 in the Aegis OSS series. The PII proxy is one of eight features in **Layer 0: Safety Foundation** — the set of protections that ship *inside* the software so that any engineer deploying Aegis gets them by default, with no docs to read and no checklist to follow.

Upcoming pieces in the Layer 0 arc:

- Article #10 — *Honey Tokens + Kill Switches: 3 Defenses for LLM Agents* (tripwires that catch prompt leaks, plus the `aegis panic` CLI)
- Article #11 — *Deploying an AI SRE Agent in a Regulated Enterprise (PIPA Case Study)* (how Layer 0.4's Ollama router keeps you on the right side of Korean law)

---

## The one-line takeaway

> If your AI agent reads production data, the moment its data *and* the LLM API live in different jurisdictions, you have a compliance problem — and you cannot solve it with a checklist. Solve it with code that runs on every call, every time, whether anyone remembers to run it or not.

— June Gu
Site Reliability Engineer
Building Aegis OSS

**Try it:**
- Repo: [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
- PII Proxy module: `apps/ai-engine/proxy/`
- Full Layer 0 spec: `docs/ARCHITECTURE.md#layer-0`

**Tags:** `AI`, `SRE`, `DevOps`, `Privacy`, `Open Source`
