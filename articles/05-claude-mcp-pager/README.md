# Article 5 — How Claude API + MCP Replaced Our 3 AM Pager: For $15/month

## What this is

Article 5 of the Aegis v4.0 Medium series. Covers Layer 3 (Claude Control Tower)
of the Aegis architecture: the extended LangGraph orchestrator, the
`investigate_with_context()` method that binds RAG + SigNoz + pattern-analyzer
context to each Claude call, the three-tier model routing (Eco Haiku /
Standard Sonnet 4.6 / Deep Opus), token-budget auto-downgrade, and the MCP
tool-category model (READ / WRITE / BLOCKED).

Leads with the 3 AM pager story (first-person, relatable) and a rendered
Slack-card mockup showing what the on-call experience actually looks like.
Closes with a full monthly cost breakdown (~$15/mo) and comparison to
vendor-hosted AI ops tools.

## Files

- `article.md` — canonical Medium-ready markdown (~3,100 words)
- `article.html` — standalone dark-theme HTML (JetBrains Mono + Inter,
  highlight.js, mermaid.js, custom Slack-card styling)

## Medium tags

`AI`, `Claude API`, `MCP`, `Incident Management`, `SRE`

## Publishing checklist

- [ ] Final scrub for account IDs / INC numbers / codename paths
- [ ] Push to Medium, set canonical URL to the GitHub article.md
- [ ] Feature image: rendered Slack card (screenshot from `article.html`)
- [ ] Cross-post the cost table to LinkedIn as a standalone graphic
- [ ] Share on r/sre and r/devops (the cost angle should resonate)
- [ ] Link back from `ARCHITECTURE.md` → Layer 3 section

## LinkedIn draft (forward ref)

A 180–220 word LinkedIn post lives in the root `linkedin-posts.md` under
"Article 5 — Claude MCP Pager." The hook is "The AI investigates at 3 AM so
I don't have to" with the before/after time-budget table. CTA links to
github.com/JIUNG9/aegis.

## Next article

Article 6 — "We Found That 80% of Our Incidents Happen on Monday 9 AM"
(Layer 2 pattern analyzer).
