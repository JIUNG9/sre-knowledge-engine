# Deploying an AI SRE Agent in a Regulated Enterprise — A PIPA Case Study

*How the amended Korean Personal Information Protection Act of April 2026 turns "LLM agents that read production data" from a nice demo into a legal minefield, and the open-source deployment pattern that keeps you on the right side of it.*

---

On April 15, 2026, the amended **Personal Information Protection Act (PIPA)** came into force in the Republic of Korea. If you work at a Korean company, or you run services that process Korean users' data, or you are thinking about where to deploy an AI agent that touches production telemetry — this article is for you.

The headline provisions everyone has been quoting:

- **Cross-border data transfers** of personal information now require an explicit consent architecture, regulator notification, and documented controller→controller agreements.
- **CEO personal liability** attaches to violations, with fines up to **3% of domestic revenue** for category-A infractions (amended, was 10% in the early draft — final bill is lower but still eye-watering).
- **Enforcement is real.** The PIPC (Personal Information Protection Commission) has already issued cessation orders against cross-border AI products in the last twelve months.

The part that nobody is writing about, which happens to be my day job, is how this intersects with **autonomous AI agents that read production telemetry**. An SRE agent that fetches a SigNoz log line — containing a real user's email or a real customer ID — and shoves it into a prompt bound for `api.anthropic.com` has just *transferred personal data to a third country without consent architecture*.

That is a compliance incident. You didn't push anything to GitHub. You didn't export a database. You just let your agent do what agents do. PIPA does not care about your intent.

This article is the deployment pattern I use for [Aegis](https://github.com/JIUNG9/aegis), my open-source AI DevSecOps platform, to keep it deployable under PIPA and comparable cross-border regimes (GDPR, Japan's APPI, India's DPDP). It is an honest engineering writeup, not legal advice — but it's the technical foundation that lets a lawyer tell you "yes, this deployment is defensible."

> **Repo:** [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
> **Deployment guide:** `docs/DEPLOYMENT.md` (Tier C)

---

## The PIPA problem, in one diagram

```
  ┌────────────────┐      ┌──────────────────┐      ┌─────────────────┐
  │                │      │                  │      │                 │
  │   SigNoz       │──┬──▶│  Aegis agent     │─────▶│  api.anthropic  │
  │   (on-prem,    │  │   │  (runs wherever  │      │  .com           │
  │    Korea)      │  │   │   you deployed)  │      │  (US or EU)     │
  │                │  │   │                  │      │                 │
  └────────────────┘  │   └──────────────────┘      └─────────────────┘
                      │
                      │   log line contains:
                      │   - real customer email
                      │   - real internal hostname
                      │   - real source IP
                      │
                      ▼
              THIS IS A CROSS-BORDER TRANSFER
```

The pattern that used to be "data in, prompt out, answer back" is now, legally, a **cross-border transfer of personal data** at each arrow that crosses a jurisdictional boundary.

Under the amended PIPA, four things are required before that transfer is lawful:

1. **A lawful basis** (consent, contract, or a specific exemption).
2. **Controller→controller agreement** with the receiving party.
3. **Notification** to PIPC in many cases.
4. **Technical safeguards** that minimize what actually crosses the border.

Points 1–3 are contractual and organizational. The lawyers handle them. **Point 4 is the engineer's job.** That is where Aegis's Layer 0 lives.

---

## The Tier C deployment pattern

Aegis ships three deployment tiers:

[IMAGE: assets/02-deployment-tiers.png — three-row deployment tier table (A Local/Homelab, B Personal Cloud, C Enterprise Sandbox) with use case and PIPA applicability per tier — Tier C row bolded to signal "this is where compliance actually matters"]

For Tier C — the "my employer expects me to deploy this without getting them sued" tier — Aegis uses five Layer 0 features together. Each one is a feature of the OSS repo, enabled via config, not a personal discipline you have to remember.

### Feature 1 — Local LLM router (the PIPA lynchpin)

Layer 0.4 is `apps/ai-engine/llm_router.py`. It classifies every prompt as *sensitive* or *sanitized* and routes accordingly:

- **Sensitive** (contains real hostnames, real PII, large log dumps, known customer names) → local Ollama running on a machine inside the same jurisdiction as the data. No HTTPS call leaves Korea.
- **Sanitized** (already-redacted placeholder text, public knowledge, demo fixtures) → Claude API in the US.

The classifier is conservative. "Borderline" counts as sensitive. A false positive costs Ollama tokens. A false negative costs a PIPA fine. The math is one-sided.

```yaml
# aegis.config.yaml (Tier C)
llm_router:
  sensitive_backend: ollama
  sanitized_backend: claude
  ollama_url: http://ollama.internal:11434   # inside VPC, inside Korea
  ollama_model: llama3.1:70b                  # serious model for serious prod
  auto_detect_sensitive: true
  always_local: false                         # flip to true for maximum conservatism
  fallback_to_cloud_on_local_failure: false   # ALWAYS false in Tier C
```

The `fallback_to_cloud_on_local_failure: false` line is the important one. If Ollama goes down, the router returns an error to the agent. It does *not* silently retry against Claude — which would be a cross-border transfer the user never authorized. Loud failure is the correct behavior when the alternative is an unlogged compliance violation.

**For the always-local paranoid mode:** set `always_local: true`. Every prompt routes to Ollama. The Claude API key remains configured (for sanitized fixtures or dev work), but at runtime, no real prompt ever reaches it.

### Feature 2 — PII redaction proxy (for the prompts that do go to Claude)

Layer 0.1 — `apps/ai-engine/proxy/` — handles the edge case where a prompt *does* go to Claude (sanitized fixture tests, demo mode, CI runs). Even in "sanitized" flows, the proxy stays on as belt-and-suspenders. If a developer accidentally tests against a real log line, the proxy catches it.

```yaml
pii_proxy:
  enabled: true               # default ON, leave it ON
  provider: hybrid            # regex + Presidio
  mapping_ttl_seconds: 3600
  custom_patterns:
    - '\bprod-[a-z0-9-]+\.example\.internal\b'
    - '\bacme_[a-z]+_prod\b'
```

Article #9 in this series has the full walkthrough of what the proxy does and doesn't catch. For a Tier C deployment, it is treated as a *secondary* defense — the primary defense is that sensitive data should never reach the cloud backend at all. The proxy catches the times that assumption fails.

### Feature 3 — OTel GenAI audit trail (for the regulator)

Layer 0.5 emits OpenTelemetry spans following the GenAI semantic conventions for every LLM call and every MCP tool invocation. The attributes are the ones PIPC cares about:

- `gen_ai.system` = `anthropic` or `ollama` (which backend served)
- `gen_ai.request.model` (which model)
- `aegis.mcp.tool.scope` = `read` or `write`
- `aegis.mcp.tool.outcome`
- Span count by backend, over time

That means if PIPC asks "prove this agent never sent personal data to a US server," you can export a trace query like:

```traceql
{ resource.service.name = "aegis"
  && span.gen_ai.system = "anthropic" } | count_over_time(1d)
```

If the answer is "zero" for the period in question, you have documentary evidence. If the answer is non-zero, you can drill into exactly which prompts went where, and (because the PII proxy was in the path) verify they were sanitized. This is the evidence a lawyer's associate builds a file around. The alternative — "trust me, it didn't happen" — is not a defense.

### Feature 4 — Honey token tripwires

Layer 0.6 plants `AEGIS-HONEY-*` strings in your agent's vault. They look like real secrets but are fake. If any of those strings ever appear in an OTel span, a Claude API request body, or a webhook payload, you have *immediate* evidence that a leak path exists — without waiting for an external breach report.

For a regulated deployment, the value is the ability to **prove a leak did not happen** (because no honey token fired in the audit window) or **prove exactly when a leak started** (first honey token hit → investigation begins → patch). Compare the usual lifecycle of a data leak (discovered months later by a third party) and the value is obvious.

### Feature 5 — Kill switch + panic CLI

Layer 0.3 — `aegis panic` — is the "stop the world" for when something goes wrong that you did not anticipate. Typing two lines:

```
$ aegis panic
Operator name: june
Reason: unusual egress to Anthropic during a scheduled outage window
```

…freezes every MCP tool the agent can invoke. If the deployer opts in, `aegis panic --revoke-aws` also attaches a `Deny *` policy to the agent's IAM role, freezing any in-flight AWS credential use.

For PIPA purposes the value is: if you ever get a PIPC inquiry, you can respond "we halted the system at TIMESTAMP while we investigate" and point at the audit log. Demonstrating operational control is part of what makes a controller-data-subject relationship defensible.

---

## What Tier C looks like in practice

Here is the deployment shape for a Korean regulated organization (I'm not going to name the employer, but the shape is real):

```
┌─────────────────────────────────────────────────────────────────┐
│  Company VPC (Korea, ap-northeast-2)                             │
│                                                                   │
│  ┌────────────┐     ┌─────────────┐     ┌──────────────────┐    │
│  │ SigNoz     │────▶│  Aegis      │◀───▶│ Ollama           │    │
│  │ (internal) │     │  agent      │     │ (llama3.1:70b)   │    │
│  └────────────┘     │  + Layer 0  │     │ on g5.12xlarge   │    │
│                     └──────┬──────┘     └──────────────────┘    │
│                            │                                      │
│                            │ SANITIZED                            │
│                            │ fixtures only                         │
│                            ▼                                      │
│                     ┌────────────┐                                │
│                     │ PII Proxy  │                                │
│                     │ (scrubs)   │                                │
│                     └──────┬─────┘                                │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                             │ outbound HTTPS
                             ▼
                     ┌────────────────┐
                     │ api.anthropic  │
                     │ .com (US)      │
                     │                │
                     │ ONLY sees      │
                     │ placeholders   │
                     └────────────────┘
```

The AWS footprint:
- **Aegis agent**: runs on a small instance inside the VPC (t3.large is sufficient for the agent itself).
- **Ollama**: runs on a g5.12xlarge or similar for the 70B model — if cost matters, gemma3:27b on a smaller GPU also works.
- **IAM**: the agent role uses the Tier C read-only policy from `deploy/iam/aws/readonly-policy.json` (Layer 0.2). No write perms. Explicit `Deny` on IAM, Secrets Manager, KMS decrypt, and every mutating verb.
- **Kill switch**: Redis inside the VPC, exposed only to Aegis.
- **OTel traces**: ship to an internal collector that forwards to the company's SigNoz (no external SaaS for trace data in Tier C).

The cost math is significant. Ollama on g5.12xlarge at on-demand pricing is ~$5/hr. A spot instance drops that to $1.50/hr. Compare to fully Claude-API-backed usage, where 100 incident investigations per day at realistic prompt sizes can run $30–50/day — so Ollama pays for itself in a few months for any non-trivial deployment, and the savings fund the compliance posture.

---

## What this buys the lawyer

Here is the conversation a legal associate can now have with PIPC:

> **PIPC:** Describe the technical safeguards in place for cross-border transfers of personal data by your AI analysis system.
>
> **Legal (with engineer's help):** Our AI analysis system is deployed such that real production telemetry — including any personal data — is processed exclusively by locally-hosted LLMs inside the Republic of Korea. Prompts containing real production data do not cross the border. Our deployment architecture enforces this at two layers: (1) an automated classifier routes all sensitive-detected prompts to local Ollama, and (2) an egress proxy redacts personal identifiers from any prompt that does leave the jurisdiction, replacing them with non-reversible placeholders. We maintain OpenTelemetry audit traces showing, per day, the number of prompts that went to each backend, along with the sensitivity classification. We can produce this audit trail for any requested time range.

Every sentence in that response maps to a shipped feature in the Aegis repo. That is the point. The lawyer is not asking you to *build* the defense at the time of inquiry — it already exists, it's already running, it's already logging.

---

## The three things that do NOT make the system PIPA-compliant

Let me be explicit about what this architecture does *not* solve:

1. **Consent and contractual basis.** The technical architecture lets you *minimize* the transfer. It does not give you a lawful basis for *any* transfer. That is a separate legal workstream — consent flows, privacy policy updates, controller agreements. Aegis does not generate those.
2. **Data subject rights.** Right to access, right to deletion, right to object — these apply to the vault contents themselves, which include logs and notes. Aegis does not implement a data-subject-request workflow; your surrounding systems have to.
3. **Cross-system breach response.** If Aegis catches a leak (honey token fires), you still have to report the incident under PIPA's 72-hour rule. The tool gives you evidence and timing; the legal response is still manual.

A lawyer looking at this architecture will be happy with it. They will still have work to do. But the work is the kind they are used to doing, rather than "we have no idea what our system is sending where."

---

## Who else this applies to

PIPA is the sharpest example, but the same pattern holds for:

- **GDPR** (EU) — Article 44–49 on international transfers. The `always_local` mode plus audit trail is functionally a "supplementary measure" in Schrems-II terms.
- **Japan's APPI** (amended 2022) — cross-border consent + safeguards similar to PIPA.
- **India's DPDP Act** (2023) — localization requirements for sensitive categories.
- **HIPAA** (US healthcare) — BAA requirements with LLM vendors, which Ollama side-steps entirely for the hot path.

For any of these, the Tier C architecture is a reasonable starting point. The config flags are the same; the auditable evidence is the same; the engineering time to deploy is the same.

---

## What's next

This is Article #11 and the close of the Layer 0 safety arc. The final piece in the series — **Article #8: Open-Sourcing Aegis: From Side Project to Platform** — is already drafted and covers the bigger story: how and why an employed SRE builds an OSS platform, what it takes to make it production-ready for strangers, and how the OSS work and the day job intersect.

Meanwhile, the engineering roadmap continues with Layers 2–5: the SigNoz connector, the Claude Control Tower, the production guardrails, and the MCP document reconciliation. Each will have its own article, each will map to a shipped feature in the repo.

---

> **If your AI agent reads production data and you operate in a regulated jurisdiction, the question is not "should I deploy defensively" — it's "have I shipped the defense, or am I hoping my users will remember to be careful." Only the first answer survives a regulator's email.**

— June Gu
Site Reliability Engineer
Building Aegis OSS

**Try it:**
- Repo: [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
- Tier C deployment guide: `docs/DEPLOYMENT.md`
- Layer 0 config reference: `docs/CONFIG.md`
- Full Layer 0 arc: Articles #9, #10, #11

**Tags:** `AI`, `Compliance`, `SRE`, `Privacy`, `Open Source`
