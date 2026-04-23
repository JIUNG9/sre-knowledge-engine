# Honey Tokens and Kill Switches — Three Defenses Before You Let AI Read Your Logs

*Your PII proxy catches the obvious leaks. These two tools catch the ones it misses — and give you a panic button when everything else has failed.*

---

In the previous piece in this series I wrote about the PII-redacting reverse proxy that sits between [Aegis](https://github.com/JIUNG9/aegis) and the Claude API. That proxy is the *everyday* defense — it scrubs emails, IPs, hostnames, and secrets out of every outbound prompt automatically.

But the proxy has known limits. It catches PII that matches a pattern. It does not catch:

- A secret in a format you have never seen before
- A confidential summary that the model paraphrases in plain English
- A social-engineering attack that convinces your agent to include the wrong file
- An MCP tool accidentally wired to do something you thought you blocked

For those, you need a *second* and a *third* defense. This article is about the other two layers I shipped in Aegis's Layer 0 safety foundation:

1. **Honey tokens** — tripwires seeded in your knowledge base that alert you if they ever leak.
2. **A kill switch with a panic CLI** — a single command that stops every agent tool and, if you opt in, attaches a `Deny *` policy to your AWS role.

Each is around 300 lines of Python. Together with the PII proxy they are the *defense-in-depth* version of "I let an LLM read my production data and I can sleep at night."

> **Repo:** [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
> **Modules:** `apps/ai-engine/honeytokens/`, `apps/ai-engine/killswitch/`

---

## Defense #1 — Honey tokens (tripwires in your own data)

A honey token is a fake credential or identifier that *should never appear anywhere* — not in a log line, not in a LLM response, not in an external system. If you ever see the string, you have hard evidence that something you thought was private leaked somewhere.

Thinkst Canarytokens has been doing this for AWS credentials for years. The pattern is old. The *new* application is planting them in the context your LLM agent reads, and monitoring every outbound hop for their presence.

### The threat model

Imagine your proxy misses a leak — a novel secret format, a cleverly worded summary, a new SigNoz field your regex doesn't know about. The leak goes to Anthropic's servers. Nothing obvious breaks. You have no idea.

Now imagine that alongside the real SigNoz data, your agent's vault contains a synthetic record like:

```yaml
# runbook: emergency-db-failover.md
...
## break-glass credentials (rotated 2026-04-12)
admin_user: aegis-honey-root-7f3a91b8c4
admin_secret: AEGIS-HONEY-SECRET-9d2e5c1a4b
```

The `aegis-honey-*` strings are fake. They map to nothing real. The LLM has no way to know they are fake, because they look like every other secret in the vault. But Aegis knows — they are registered in a local SQLite file — and Aegis scans every outbound payload and every OTel trace for them.

If any of those strings ever show up in:

- A Claude API request body
- An OTel span attribute
- An external webhook payload
- A log line on your SIEM

You receive an immediate alert. You now *know* you have a leak. You can see exactly where the leak surfaced. You can reproduce and patch.

### How the module works

Three pieces:

```python
# apps/ai-engine/honeytokens/generator.py

CATEGORIES = Literal[
    "aws_key", "email", "hostname",
    "db_password", "api_key", "pem_block",
]

@dataclass
class HoneyToken:
    id: str                 # sha256[:12] — globally unique
    category: str
    value: str              # the string we plant in the data
    created_at: datetime
    seeded_in: list[str]    # where we planted it (for debugging)

class HoneyTokenGenerator:
    def create(self, category: CATEGORIES) -> HoneyToken:
        token_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
        value = self._render(category, token_id)
        self._registry.insert(HoneyToken(id=token_id, category=category, value=value, ...))
        return ...
```

The render step produces something that looks like the category — an AWS key becomes `AKIA` + 16 random chars, a PEM block becomes a full-looking PEM with a marker in the subject, etc. The twist: every value contains the substring `AEGIS-HONEY-{token_id}` somewhere inside, so the scanner can find it with O(n) multi-pattern matching even on large payloads.

```python
# apps/ai-engine/honeytokens/scanner.py

class OutboundScanner:
    def __init__(self, registry: HoneyTokenRegistry):
        self._automaton = ahocorasick.Automaton()
        for token in registry.all():
            self._automaton.add_word(token.value, token.id)
        self._automaton.make_automaton()

    def scan(self, text: str) -> list[HoneyTokenHit]:
        return [
            HoneyTokenHit(token_id=token_id, offset=offset, context=text[offset-40:offset+40])
            for offset, (token_id,) in self._automaton.iter(text)
        ]
```

Aho-Corasick gives us O(n) time regardless of registry size — so even a thousand honey tokens scanning a megabyte payload adds well under a millisecond. The scanner is wired into the PII proxy, the MCP tool dispatcher, and an OTel span processor. Every outbound byte gets checked.

When a hit fires, three things happen:

1. An OTel span is emitted with error status and the token category
2. A webhook POST goes to your alert endpoint if configured
3. A loud stderr warning in ANSI red surfaces on the operator console

You can choose not to alert — some people just want to see the span show up in Jaeger — but the default is "scream."

### What this is *not*

It is not a prevention. It is a detection. The leak still happens. The value is that you *know* it happened, within milliseconds, with full context. Compared to the usual "we learned a year later from a breach report" timeline, that is a significant upgrade.

---

## Defense #3 — The kill switch and `aegis panic`

The proxy catches obvious leaks. The honey tokens catch the subtle ones. What stops an agent that is *actively misbehaving right now*?

Nothing, unless you build it. So I did.

### The model

A simple flag, checked on every MCP tool invocation, with three backends:

- **Redis** (default) — `GET aegis:killswitch` in under 5ms
- **File** (fallback when Redis is down) — one stat() call per tool
- **Explicit revoke** (opt-in, nuclear) — attach an IAM inline policy that denies everything

```python
# apps/ai-engine/killswitch/switch.py

class KillSwitch:
    def trip(self, reason: str, operator: str) -> None:
        payload = {"active": True, "reason": reason, "operator": operator, "at": now()}
        self._backend.set("aegis:killswitch", json.dumps(payload))
        self._audit.append({"event": "trip", **payload})

    def is_active(self) -> bool:
        raw = self._backend.get("aegis:killswitch")
        return bool(raw and json.loads(raw).get("active"))
```

Every MCP tool is decorated:

```python
# apps/ai-engine/killswitch/gate.py

def killswitch_gate(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if killswitch.is_active():
            status = killswitch.status()
            raise KillSwitchTripped(
                f"Aegis is halted (tripped by {status['operator']}): {status['reason']}"
            )
        return func(*args, **kwargs)
    return wrapper
```

Every MCP tool — read, write, whatever — calls through this decorator before doing anything. If the switch is active, the tool raises before making a single HTTP call, touching a single resource, or invoking a single other tool.

### The `aegis panic` CLI

```
$ aegis panic
Operator name: june
Reason: seeing unexpected S3 list calls in Datadog
[y/N] Also revoke AWS session for arn:aws:iam::123456789012:role/aegis? (requires boto3) y

[!] KILL SWITCH TRIPPED at 2026-04-21T14:07:33+09:00
[!] Reason: seeing unexpected S3 list calls in Datadog
[!] AWS role aegis-readonly: attached deny-all session policy
[!] All 37 loaded MCP tools will refuse calls until released.

Audit log: ./aegis-audit.jsonl
Release:   aegis release
```

Two typed lines and the agent is frozen. If you opted in, the AWS role is also frozen — any in-flight session using that role starts receiving `AccessDenied` on its next API call.

### Why "opt in" on the AWS revoke

Because panic buttons with side effects get tested. If the default was "also revoke AWS credentials," someone would run `aegis panic` during a demo to show how it works, and that someone would have a bad day. Explicit opt-in means the revoke path runs when the operator meant it to run. For most deployments the in-process kill switch is enough. For a deployment where the agent role can read sensitive data that an attacker could exfiltrate in the milliseconds it takes to notice, the AWS revoke path buys time.

### Graceful degradation

Redis going down should not disable the kill switch — that would be the worst possible failure mode. The switch checks Redis first, and if Redis returns an error, it falls back to the file backend and logs a warning. Both backends are authoritative; whichever is active wins.

Tests use `fakeredis` so CI does not need a real Redis. The `aegis panic` CLI is tested with Typer's `CliRunner`. The AWS revoke path is tested against moto.

---

## How the three defenses compose

Here is the mental model for why you want all three:

[IMAGE: assets/02-defense-layers.png — three-row defense-in-depth table showing the PII proxy, honey tokens, and kill switch side-by-side: what each catches, what each misses, and response time per layer (0ms prevention, ~1ms detection, ~5ms check + ~2s halt)]

You want the proxy because it prevents the common case cheaply. You want honey tokens because the proxy is not perfect and you need *some* way to know when it misses. You want the kill switch because sometimes you see something weird in your telemetry and you need to stop the world *now* while you figure out what it was.

One without the others leaves a hole. All three together give you something that can legitimately be called "safe to deploy against production data."

---

## What you do with it

Install:

```bash
pip install -e "apps/ai-engine[safety]"
```

Seed some honey tokens into your demo vault:

```bash
aegis honeytokens seed --vault ~/Documents/obsidian-sre --per-category 3
```

This creates three fake AWS keys, three fake emails, three fake hostnames, etc., each with a unique `AEGIS-HONEY-*` marker, registered in `./honeytokens.db`. They are scattered across your real vault pages in realistic-looking positions — the idea is that a human browsing the vault would not immediately spot them, but the scanner can.

Run your agent. The proxy and the scanner run on every outbound call. Any honey token hit fires an alert.

If something goes wrong, panic:

```bash
aegis panic
```

Release after you have investigated:

```bash
aegis release
```

---

## A note on threat modeling

These three tools are designed against **operator mistakes** and **agent misconfigurations**, not against **nation-state adversaries**. Someone who owns your laptop can disable any of them. Someone who controls your Anthropic API key can do whatever they want. The point is to raise the bar from "a single oversight leaks your prod data forever" to "you have to make three independent mistakes to lose."

For the kinds of mistakes I have actually made in production over the years, three layers is enough. Your threat model may differ. The point is that the rules I used to hold in my head — sanitize, watch for leaks, have a way to stop the agent — are now three shipped features in the repo. Anyone who deploys Aegis gets them, whether they read the docs or not.

That is the Layer 0 thesis.

---

## What's next in the series

- Article #11 — *Deploying an AI SRE Agent in a Regulated Enterprise (PIPA Case Study)* — how I use all of the above, plus Layer 0.4's Ollama router, to keep Aegis on the right side of the amended Korean Personal Information Protection Act.

---

> **The cheapest time to catch a leak is before it leaves the laptop. The second cheapest time is a millisecond later, when a honey token trips. The third cheapest is while it is still happening, with a panic command. Any deployment of an AI agent over production data should have all three.**

— June Gu
Site Reliability Engineer, my employer
Building Aegis OSS

**Try it:**
- Repo: [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
- Honey tokens: `apps/ai-engine/honeytokens/`
- Kill switch: `apps/ai-engine/killswitch/`
- Panic CLI: `aegis panic`

**Tags:** `AI`, `SRE`, `Security`, `LLM`, `Open Source`
