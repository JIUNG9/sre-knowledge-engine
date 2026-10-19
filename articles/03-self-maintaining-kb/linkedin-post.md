# LinkedIn — Article 3: Self-Maintaining KB

Three variants. Pick one. Each targets 1,300 characters. No emojis. CTA to Medium + GitHub.

---

## Variant A — Technical

**I built an SRE knowledge base that updates itself. The vault at github.com/JIUNG9/aegis-wiki is the live output.**

The design is boring on purpose. An Obsidian vault on disk. A Python engine that ingests runbooks, Confluence pages, and resolved SigNoz incidents. A synthesizer that merges each source into canonical Markdown. A staleness linter with per-source-type rules. A publisher that commits and pushes to GitHub.

When a new incident resolves, the engine writes its RCA into the relevant entity page. When Confluence updates an architecture doc, the engine re-synthesizes any dependent wiki pages and flags contradictions. Pages not touched by any source in 90 days get a staleness warning. Pages abandoned for 180 days auto-archive with a reason.

The vault is my portfolio. The engine is open source. Claude Haiku handles synthesis, Sonnet handles contradiction detection. Runs at about 2 USD a month for a 100-page vault.

Full write-up with the data model, the staleness rules, and the publisher safety checks: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #KnowledgeManagement #Obsidian

---

## Variant B — Career

**I turned my SRE work into a self-maintaining public portfolio. Same tool does both.**

The vault at github.com/JIUNG9/aegis-wiki is a live Obsidian directory of SRE entities, concepts, incidents, and runbooks from four years of operating production systems. The engine at github.com/JIUNG9/aegis reads sources once, synthesizes them into pages, and publishes the result.

Why build it this way? Two reasons.

One — every SRE hiring manager wants to see the same three things. Do you operate production? Can you write a runbook? Can you build systems, not just run them? The vault answers all three.

Two — the engine solves a real problem I lived with for years. Runbooks rot. Confluence dies. The AI agents pointed at those docs answer from fossils. The LLM Wiki pattern fixes it.

If you are hiring SREs who ship, I am open to conversations. Relocating to Canada in 2027.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #Portfolio #OpenSource

---

## Variant C — Hot take

**Your wiki is dead. It died in 2023. You just have not noticed yet.**

Everyone has the same Confluence graveyard. The last edit on the auth-service architecture page is nineteen months old. The runbook for the payment service references a team that was reorganized out of existence. Half the links are 404.

This is the default state of every SRE wiki I have ever seen. Knowledge enters. Nothing exits. Staleness compounds.

I got tired of it and built a self-maintaining alternative. Obsidian vault on disk. LLM synthesizes each new source into canonical pages. Staleness linter flags anything older than 90 days. Publisher pushes to GitHub. The vault is the portfolio — github.com/JIUNG9/aegis-wiki — the engine is open source at github.com/JIUNG9/aegis.

Cost: under two dollars a month for 100 pages. Easier than writing another doc nobody will read.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#KnowledgeManagement #SRE #AIEngineering
