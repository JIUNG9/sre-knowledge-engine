# Article 03 — Self-Maintaining SRE Knowledge Base

## What this is

The Obsidian-centric companion piece to Article 02. Where Article 02 was about reconciliation (defensive), Article 03 is about auto-maintenance (generative). Shows the vault architecture (entities/concepts/runbooks/incidents), the auto-sync loops from SigNoz and Confluence, the living `overview.md` fence pattern, and freshness + orphan detection.

Closes with the career angle: the sanitized public mirror at `github.com/JIUNG9/aegis-wiki` as a portfolio artifact. "When a recruiter visits my GitHub, they see a live, real-looking SRE knowledge base." This is the article most directly tied to the Canada job-search pipeline — it argues the vault itself is portfolio evidence that an SRE lead wants to see.

References real built code: `signoz_sync.py`, `confluence_sync.py`, `synthesizer.py`, `staleness.py`, `publisher.py` — all in `apps/ai-engine/wiki/`.

## Medium tags

- Obsidian
- Knowledge Management
- AI
- SRE
- Open Source
- Career

## Publishing checklist

- [ ] Import `article.md` into Medium draft
- [ ] Verify all `github.com/JIUNG9/aegis` and `github.com/JIUNG9/aegis-wiki` links resolve
- [ ] Confirm Mermaid flowchart renders cleanly (fallback: screenshot to PNG)
- [ ] Add canonical link to hosted `article.html`
- [ ] Stagger publish 3-5 days after Article 02 for series momentum
- [ ] Schedule publish Wednesday 09:00 ET
- [ ] Pin to Medium profile as career-forward piece
- [ ] Cross-post to `r/ObsidianMD`, `r/sre`, LinkedIn
- [ ] LinkedIn post draft: see `../linkedin-posts/03-self-maintaining-kb.md` (forthcoming)
- [ ] Add to `aegis-wiki` repo README as "Origin article"

## Assets

- `article.md` — Medium-ready source
- `article.html` — standalone styled version for personal site hosting

## Word count target

2,600–3,000 words (see grep report in parent task).
