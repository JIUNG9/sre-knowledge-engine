# LinkedIn — Article 1: Karpathy Killed RAG

Three variants. Pick one. Each targets 1,300 characters. No emojis. CTA to Medium + GitHub.

---

## Variant A — Technical

**Your RAG pipeline is the wrong shape for operational knowledge.**

Chunk, embed, top-k retrieve. That design returns the three highest-scoring fragments at query time — with no notion of which one is current, which one contradicts the others, or which one was written by an engineer who left the company in 2023.

For an SRE agent, that is a production incident waiting to happen.

I rebuilt ours using the Karpathy LLM Wiki pattern. Every source — runbook, post-mortem, Confluence page, resolved SigNoz incident — gets read exactly once by Claude Haiku. The model synthesizes it into a canonical Obsidian page. Contradictions are flagged at ingest, not at query. Staleness is tracked per source.

Queries hit pre-synthesized knowledge, not raw chunks.

Cost at 100 pages with daily sync: about 2 USD a month. The vault is public at github.com/JIUNG9/aegis-wiki — the engine is open source.

Full write-up with the ingest-time contradiction prompt, the staleness rules, and the trade-offs vs. classic RAG: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #AIEngineering #KnowledgeManagement

---

## Variant B — Career

**I got tired of watching SRE chatbots confidently quote two-year-old runbooks.**

So I built something different. Aegis is an open-source AI-Native DevSecOps command center. Layer 1 — the LLM Wiki — is the part I spent the most time on, because it is the part every other "AI for SRE" product gets wrong.

It implements Andrej Karpathy's LLM Wiki pattern: the model reads each source once, writes a canonical page, flags contradictions, tracks staleness. The vault is an Obsidian directory I edit locally and the engine syncs to GitHub automatically.

I run production SRE by day — multi-account AWS, EKS, ArgoCD, SigNoz. The operational lessons go directly into Aegis by night. The vault at github.com/JIUNG9/aegis-wiki is both the portfolio and the product.

If you are hiring SREs who can build systems and not just operate them, I am open to conversations — relocating to Canada in 2027.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #PlatformEngineering #OpenSource

---

## Variant C — Hot take

**Your RAG system is serving two-year-old docs as truth. And the AI has no idea.**

Every "AI for DevOps" pitch I have seen this year is the same diagram. Ingest runbooks. Chunk. Embed. Top-k at query time. Ship.

That design is fundamentally wrong for SRE work.

The docs are stale. Two runbooks contradict each other. The post-mortem is in Google Docs, the runbook is in Confluence, the architecture decision is in a GitHub README from 2022. The retrieval layer sees none of that. It returns three fragments by cosine similarity and the agent answers with confidence.

Andrej Karpathy named the fix on X: stop treating docs as a bag of chunks. Let the LLM read each source once and synthesize a canonical wiki page. Catch contradictions at ingest, not at query. Track staleness per source. Let knowledge compound.

I built this into Aegis. It costs 2 USD a month. It replaces the RAG layer entirely.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#RAG #AIEngineering #SRE
