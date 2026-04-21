# Aegis LLM Router — Layer 0.4

**Problem.** Aegis reads live production telemetry (SigNoz logs, AWS resources, Confluence docs). Sending that to a US-hosted LLM is a cross-border transfer — under the Korean PIPA Sep-2026 amendment, that requires explicit consent or a localization waiver. For regulated tenants, the safer design is to keep prod data on-prem and route sanitized content to Claude.

**Solution.** Every LLM call goes through `LLMRouter`. The router classifies the prompt and dispatches to one of two backends:

- **Ollama** (local, `http://localhost:11434`) — for sensitive prompts.
- **Claude API** — for sanitized prompts.

Backends return a unified `RouterResponse` so callers don't care which served the request. Streaming is supported on both.

## Decision tree

```
prompt
  |
  +-- config.always_local ........................ OLLAMA (kill-switch)
  +-- mode == "local" ............................ OLLAMA
  +-- mode == "cloud" ............................ CLAUDE
  +-- sensitivity_override == True ............... OLLAMA
  +-- sensitivity_override == False .............. CLAUDE
  +-- auto_detect: classify_sensitivity(text)
         |
         +-- level == "sensitive"  ............... OLLAMA
         +-- level == "borderline" ............... OLLAMA (safe default)
         +-- level == "sanitized"  ............... CLAUDE
  +-- otherwise .................................. CLAUDE (sanitized backend)
```

## Sensitivity signals

Hostnames (real FQDN) • k8s pod names • AWS account IDs / ARNs • emails (non-`example.com`) • IPv4 (non-RFC5737) • Korean resident numbers • credit-card-shaped digits • auth headers • deployment-specific keywords you supply (your company name, customer codenames) • large payloads.

Sanitized markers (`<USER_1>`, `REDACTED`, `example.com`) push toward sanitized.

## Fallback policy

When Ollama is unreachable the router **fails loudly by default**. Silent fallback to Claude could leak prod data cross-border, which is strictly worse than a 503. Operators can opt into fallback via `fallback_to_cloud_on_local_failure=True` — a warning is logged every time it triggers.

## Auditability

Every routing decision is logged at INFO with the driving signals, so an auditor can trace which prompts went where and why.
