# LinkedIn Announcement — Article #10

Three variants. Pin for 1 week.

---

## Variant 1 — Technical (default)

Last week I wrote about the PII-redacting reverse proxy I put between my open-source SRE agent and the Claude API.

The proxy catches the common case. It does not catch everything.

So this week I shipped the other two layers of the Aegis Layer 0 safety foundation:

• **Honey tokens** — tripwires I seed in the agent's knowledge base. Fake AWS keys, fake internal hostnames, fake emails, all containing `AEGIS-HONEY-{hash}` markers. A scanner based on Aho-Corasick checks every outbound byte. If any marker shows up in a Claude API request, an OTel span, or a webhook payload, I get an immediate alert with full context. ~1 ms per scan regardless of registry size.

• **Kill switch + `aegis panic`** — a Redis-backed flag every MCP tool checks before executing. Typing `aegis panic` freezes the agent, optionally attaches a `Deny *` policy to its AWS role. Graceful fallback to a file backend if Redis is down.

Together with the PII proxy these make up Layer 0 — the safety primitives that ship *inside* the repo so any engineer who clones Aegis gets them by default.

Prevention. Detection. Response. Three layers, one repo, ~1000 lines of Python total.

Full article:
[Medium URL]

Source: github.com/JIUNG9/aegis

Next: deploying this thing in a regulated enterprise (PIPA case study).

#SRE #AISafety #OpenSource #DevOps

---

## Variant 2 — Career / thesis angle

The rules I kept in my head about running an AI agent safely — "remember to sanitize," "remember to watch for leaks," "remember to have a way to stop it" — were three bugs waiting for three bad days.

So I turned all three into code.

• Prevention — PII proxy, ~400 lines (Article #9)
• Detection — honey token tripwires, ~300 lines (this article)
• Response — kill switch + panic CLI, ~300 lines (this article)

None of these are novel ideas. Thinkst has sold canary tokens for a decade. Kill switches are a Linux kernel pattern. The novel part is shipping them *together*, *inside* an open-source AI agent, so any engineer deploying the agent inherits the protections without having to read docs.

Layer 0 of my Aegis platform.

[Medium URL]

github.com/JIUNG9/aegis

#EngineeringLeadership #AISafety #OpenSource

---

## Variant 3 — Hot take

Most AI-agent repos I have looked at have three safety messages:

1. "Don't point this at production."
2. "Be careful with prompt injection."
3. "Remember to sanitize data."

These are all admissions of defeat. "Don't point this at production" means the tool is not deployable. "Be careful" means we have no protection. "Remember" means we are relying on humans.

I am building the opposite — an AI SRE platform that ships with three *active* defenses against the problems that actually happen: data leaks (PII proxy), undetected exfiltration (honey tokens), runaway behavior (kill switch + panic CLI).

Full architecture:
[Medium URL]

github.com/JIUNG9/aegis

Deploy it at a hospital. Deploy it at a bank. Deploy it where compliance matters. It is designed to be deployable there.

#AI #SRE #Compliance #OpenSource
