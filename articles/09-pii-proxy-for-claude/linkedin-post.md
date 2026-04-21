# LinkedIn Announcement — Article #9

Three variants. Pick one based on desired tone. Pin for 1 week after posting. Post within 1 hour of Medium publish.

---

## Variant 1 — Technical (default)

I was wiring up Layer 3 of my open-source AI SRE platform last weekend when I tailed my outbound HTTPS traffic and saw a real coworker's email in a prompt headed to `api.anthropic.com`.

Nothing was committed. The GitHub repo was clean. But production data had already left Korea — because the agent fetched a log line on its own and shoved it into the prompt.

So I wrote a 400-line reverse proxy that:
• Scans every outbound message for PII, AWS keys, internal hostnames, JWTs, PEM blocks
• Replaces them with deterministic placeholders (`<USER_1>`, `<HOST_1>`, `<IP_1>`)
• Reverse-substitutes the real values when Claude's response comes back
• Is enabled by default, so no engineer has to remember to sanitize anything

This is Layer 0.1 of Aegis — the part of the repo that makes the platform deployable under Korean PIPA (and, frankly, GDPR) without turning compliance into a checklist that someone inevitably skips.

Full article, threat model, and architecture:
[Medium URL]

Source: github.com/JIUNG9/aegis — module `apps/ai-engine/proxy/`

Next in the series: honey tokens + kill switches, and a PIPA deployment case study.

#SRE #DevOps #LLM #Privacy #OpenSource

---

## Variant 2 — Career / Leadership angle

"Sanitize data before sending prompts to the LLM."

That's not a design. That's a prayer.

It works fine when the LLM is a chat window you paste into — there's an obvious checkpoint (you, looking at the screen). It does not work when the LLM is an autonomous agent that fetches its own context from ten sources and fires API calls on its own.

After spending the weekend on Layer 3 of my open-source AI SRE platform, I realized every safety rule I was holding in my head ("remember to scrub the log line", "remember to redact the email") was a bug waiting for a bad day.

So I turned the rule into code. 400 lines of Python, one reverse proxy, enabled by default. Every outbound call gets scrubbed whether anyone remembers or not.

Full writeup — architecture, threat model, Korean PIPA implications:
[Medium URL]

This is Layer 0.1 in a larger OSS platform built so any engineer can clone it and deploy safely. The rule I follow in my head is now a rule the software enforces.

#SRE #EngineeringLeadership #AISafety #OpenSource

---

## Variant 3 — Hot take / contrarian

Every AI-agent tutorial I've read ends with a line like "remember to sanitize sensitive data before sending prompts to the LLM."

That line is a compliance time bomb.

If your agent reads production data on its own — which, let's be honest, is the whole point of an autonomous agent — then the moment the agent and the LLM API live in different jurisdictions, you have a cross-border data transfer problem that a checklist cannot solve.

Korean PIPA's April 2026 amendment ties CEO personal liability to exactly this scenario. GDPR is similar. Nobody in the agent-framework space is talking about it.

I wrote a 400-line reverse proxy that sits between my open-source SRE agent (Aegis) and `api.anthropic.com`, scrubs PII on the way out, and reverses the mapping on the way in. It's Layer 0.1 of a safety foundation that ships *in the repo*, not in the docs, because the docs get skipped.

Full writeup + threat model + code:
[Medium URL]

Source: github.com/JIUNG9/aegis

#AI #Compliance #SRE #PIPA #GDPR
