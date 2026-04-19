# Article 02 — Your AI Agent is Lying

## What this is

The flagship practical article in the Aegis OSS series. Opens with a concrete near-miss (AI suggesting `kubectl scale --replicas=0` on `auth-service` from a 2023 Confluence draft), diagnoses why scattered docs + confident LLMs is a dangerous combination, and walks through the document reconciliation engine we built to solve it.

Anchors to real built code in `apps/ai-engine/wiki/` (Layer 1) — `contradiction.py`, `staleness.py`, `confluence_sync.py`, `signoz_sync.py` — and forward-refs the Layer 5 MCP tool-set (`mcp/tools/docs_reconciliation.py` — planned) with explicit "coming in Layer 5, see the roadmap" framing. No false claims.

## Medium tags

- AI
- DevOps
- Documentation
- MCP
- SRE

## Publishing checklist

- [ ] Import `article.md` into Medium draft
- [ ] Verify all `github.com/JIUNG9/aegis` links resolve
- [ ] Confirm Mermaid diagram renders (may need to re-paste as image for Medium)
- [ ] Add canonical link to `article.html` hosted version once live
- [ ] Set subtitle from first line of md file
- [ ] Schedule publish for Tuesday 09:00 ET (peak SRE-community traffic window)
- [ ] Cross-post link to `r/sre`, `r/devops`, `Hacker News`
- [ ] LinkedIn post draft: see `../linkedin-posts/02-ai-is-lying.md` (forthcoming)
- [ ] Add to Aegis repo README "Articles" section

## Assets

- `article.md` — Medium-ready source
- `article.html` — standalone styled version for personal site hosting

## Word count target

2,800–3,200 words (see grep report in parent task).
