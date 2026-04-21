# Article #9 — I Built a PII-Redacting Proxy for Claude

Layer 0 of the Aegis v4.0 article series. Explains why an AI SRE agent that reads prod data is one HTTPS call away from a cross-border compliance incident, and walks through the reverse proxy that ships in `apps/ai-engine/proxy/` to prevent it.

## Files

| File | Purpose |
|------|---------|
| `article.md` | Canonical Medium markdown source |
| `article.html` | Standalone dark-theme HTML preview |
| `linkedin-post.md` | LinkedIn announcement draft (3 variants) |
| `assets/` | Screenshots + architecture diagram (PNG exports) |

## Where to publish

**Medium** — June Gu's profile.

**Tags (Medium allows 5):** `AI`, `SRE`, `DevOps`, `Privacy`, `Open Source`.

Additional tags inside the article body: `LLM`, `Compliance`, `Claude`, `Anthropic`, `PIPA`.

## Publishing checklist

- [ ] Final proofread on desktop + mobile width
- [ ] Verify every GitHub link resolves (`github.com/JIUNG9/aegis/apps/ai-engine/proxy/*`)
- [ ] Confirm Mermaid / ASCII diagram renders correctly in Medium preview
- [ ] Paste into Medium, preview, select 2-3 pull quotes
- [ ] Feature image (terminal-green proxy-flow diagram)
- [ ] Schedule Tuesday or Wednesday 9 AM ET (Canadian recruiter prime time)
- [ ] Crosspost LinkedIn within 1 hour using `linkedin-post.md`
- [ ] Pin LinkedIn post for 1 week
- [ ] Add to canada-relocation-strategy.md content log

## Cross-references

- Source code: `apps/ai-engine/proxy/` in [github.com/JIUNG9/aegis](https://github.com/JIUNG9/aegis)
- Follow-up: Article #10 (honey tokens + kill switches) and #11 (PIPA case study)
- Predecessors: Articles #1–#8 established the architecture; this is the first of the Layer 0 safety arc.

## Notes

- No emojis.
- No Claude co-author lines.
- Sanitized — no real acme-corp/a large tech company/a large e-commerce company account IDs, hostnames, or incident identifiers.
- The Korean coworker email example (`kim.jiho@example.com`) is a synthetic illustration, not a real person.
