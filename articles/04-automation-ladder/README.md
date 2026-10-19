# Article 4 — AI SRE Agent That Watches Before It Acts: The 4-Stage Automation Ladder

## What this is

Article 4 of the Aegis v4.0 Medium series. Covers Layer 4 (Guardrails) of the
Aegis architecture: observation-mode ladder (OBSERVE → RECOMMEND → LOW-AUTO →
FULL-AUTO), risk classification, dry-run pre-validation, metrics-based
post-validation, Slack approval gates, and SOC2-compliant audit logging.

The framing is the trust-building arc: "don't let an AI agent touch production
on day one." Mixes the Conf42 SRE 2026 safety-first pattern with a week-by-week
story of rolling this out on a real production team.

## Files

- `article.md` — canonical Medium-ready markdown (~3,000 words)
- `article.html` — standalone dark-theme HTML (JetBrains Mono + Inter,
  highlight.js, mermaid.js)

## Medium tags

`AI`, `SRE`, `DevOps`, `Automation`, `Safety`

## Publishing checklist

- [ ] Final scrub for account IDs / INC numbers / codename paths
- [ ] Push to Medium, set canonical URL to the GitHub article.md
- [ ] Feature image: guardrails ladder diagram (render from the mermaid flow)
- [ ] Cross-post an abridged version to LinkedIn (see forward ref below)
- [ ] Share in the Aegis GitHub discussions as the Layer 4 explainer
- [ ] Add link back from `ARCHITECTURE.md` → Layer 4 section

## LinkedIn draft (forward ref)

A 180–220 word LinkedIn post lives in the root `linkedin-posts.md` under
"Article 4 — Automation Ladder." The hook is the "thank god it didn't act"
week-7 moment. CTA links to github.com/JIUNG9/aegis.

## Next article

Article 5 — "How Claude API + MCP Replaced Our 3 AM Pager — For $15/month"
(Layer 3 Control Tower).
