# LinkedIn — Article 8: Open-Sourcing Aegis

Three variants. Pick one. Each targets 1,300 characters. No emojis. CTA to Medium + GitHub.

---

## Variant A — Technical

**I am open-sourcing Aegis — an AI-native DevSecOps command center with a five-layer architecture and a fifteen-dollar-a-month cost envelope.**

Layer 1 — LLM Wiki, Karpathy pattern, built. Obsidian vault on disk, synthesizer writes canonical pages, contradiction detector flags conflicts at ingest, staleness linter enforces freshness. Published at github.com/JIUNG9/aegis-wiki as a live portfolio.

Layer 2 — SigNoz connector, HTTP-only, with a pattern analyzer that aggregates incidents by hour of week, service correlation, and deployment regression.

Layer 3 — Claude Control Tower. Three modes: Eco (Haiku), Standard (Sonnet), Deep (Opus). Budget cap with auto-downgrade.

Layer 4 — Production guardrails. Four-stage automation ladder, risk classifier, pre-validation dry-run, post-validation metric check, SOC2-style audit trail.

Layer 5 — MCP document reconciliation. Confluence sync, GitHub scan, incident coverage check, contradiction lint.

The stack: Next.js 16 frontend, Go Fiber API, Python FastAPI for the AI engine. Postgres, ClickHouse, Redis via docker-compose.

Code, architecture, and an eight-part series walking through every layer: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#OpenSource #SRE #PlatformEngineering

---

## Variant B — Career

**Four years of production SRE work, compiled into a five-layer open-source platform. Today I am publishing it.**

Aegis is the side project I would have wanted as a reference when I started SRE work. A Karpathy-style LLM Wiki instead of chunk-based RAG. A SigNoz connector with time-based pattern analysis. A four-stage automation ladder that earns production access. Production guardrails with a SOC2-style audit trail. MCP tools that reconcile Confluence with GitHub with incident history.

The full stack is open source. The wiki it produces is at github.com/JIUNG9/aegis-wiki — a live portfolio vault that doubles as the platform's own dogfood.

I am relocating to Canada in 2027. If you run an SRE or platform team and you want to see how I think about incident response, knowledge management, and AI safety, the repo is the strongest answer I can give you.

Full article — the career story plus the engineering decisions: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #OpenSource #Career

---

## Variant C — Hot take

**Platform engineering is the top trend in every analyst report. Most platforms I have seen are a Backstage fork and a wiki nobody reads.**

Aegis is different on purpose. Every "AI for SRE" product ships chunk-based RAG as the knowledge layer, which is fundamentally wrong for operational work. Every agentic demo skips the part where the agent can delete production. Every wiki is dead within a year.

Aegis fixes all three. Karpathy LLM Wiki instead of RAG. Four-stage automation ladder instead of day-one autonomy. A self-maintaining vault that updates from real sources instead of a Confluence graveyard.

Five layers, fifteen dollars a month, fully open source. Built while running SRE in production by day. The wiki it produces is my portfolio at github.com/JIUNG9/aegis-wiki — the engine is at github.com/JIUNG9/aegis.

If the bar for platform engineering is higher than "a Backstage fork," this is my attempt at clearing it.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#PlatformEngineering #OpenSource #SRE
