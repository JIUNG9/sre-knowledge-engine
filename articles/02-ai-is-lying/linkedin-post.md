# LinkedIn — Article 2: Your AI Agent Is Lying

Three variants. Pick one. Each targets 1,300 characters. No emojis. CTA to Medium + GitHub.

---

## Variant A — Technical

**We ran a reconciliation pass across our runbooks, Confluence space, and GitHub docs. The agent had been answering from documents that disagreed with each other for over a year.**

This is the contradiction problem. A runbook says "restart the pods." The Confluence page says "scale to zero and back." The post-mortem says neither — it says the fix was a DNS cache flush. The RAG retriever has no opinion. It returns whatever scores highest.

Aegis Layer 5 is four MCP tools that fix this:

- confluence_sync: crawl the space, flag pages untouched for 90+ days
- github_docs_scan: find orphaned .md files with no inbound links
- incident_history_sync: match resolved incidents against runbook coverage
- docs_lint: cross-reference all sources, produce a reconciliation report

The report lists contradictions, coverage gaps, and stale pages with reasons. The Wiki engine can auto-archive beyond 180 days. The SRE reviews the rest.

On my own docs the first pass flagged 12 stale Confluence pages, 5 orphaned GitHub docs, and 3 runbooks that did not cover recently resolved incident classes.

Full write-up with the MCP tool definitions and the reconciliation prompt: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #DocumentManagement #MCP

---

## Variant B — Career

**Every SRE team I have worked with has the same doc graveyard. So I built the cleanup crew.**

Runbooks scattered across three GitHub repos. Confluence pages from 2023 that nobody updates. Post-mortems in Google Docs that were never linked to the runbooks they should have triggered. Tribal knowledge stuck in Slack threads.

The AI agent that answers "how do we respond to this alert" treats all of it as ground truth. That is the lying problem.

Aegis Layer 5 is a set of MCP tools that reconcile these sources into a single source of truth. Confluence sync with staleness rules. GitHub scan with orphan detection. Incident coverage gaps. A lint pass that flags contradictions for human review.

At my day job I have been the on-call engineer woken up by a runbook that referenced a deprecated service. That incident is why this layer exists.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #PlatformEngineering #AIEngineering

---

## Variant C — Hot take

**Your AI agent is lying. It is referencing docs from 2023 and presenting them as truth.**

Every team I have talked to this year has the same setup. Confluence with four-year-old pages. GitHub runbooks that reference services that were decommissioned a year ago. Post-mortems nobody ever linked back to the runbook they should have updated.

The RAG agent sees all of it. Top-k retrieval gives no weight to freshness, no weight to cross-document consistency, and zero credit to the engineer who wrote the current answer in Slack yesterday.

So the agent answers with confidence. From fossils.

The fix is not a better embedding model. The fix is a reconciliation layer — MCP tools that sync Confluence, scan GitHub, match incidents to runbooks, and produce a contradiction report. Read each source once. Catch the lie at ingest time.

On my own docs: 12 stale Confluence pages, 5 orphaned GitHub docs, 3 runbooks missing incident classes. One pass.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#AI #DevOps #KnowledgeManagement
