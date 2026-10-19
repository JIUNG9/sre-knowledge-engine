# Article #11 — PIPA Case Study (Regulated Enterprise Deployment)

Final article in the Layer 0 safety arc. Ties together Layers 0.1 (PII proxy), 0.3 (kill switch), 0.4 (local LLM router), 0.5 (OTel audit), 0.6 (honey tokens) into a defensible deployment pattern for Korean PIPA compliance.

## Files

| File | Purpose |
|------|---------|
| `article.md` | Canonical Medium markdown |
| `article.html` | Standalone dark-theme HTML preview |
| `linkedin-post.md` | LinkedIn announcement (3 variants, one heavily legal-leaning) |
| `assets/` | Tier C architecture diagram (PNG) |

## Where to publish

**Medium** — June Gu's profile. Publish LAST among Layer 0 articles (sequence: #9 → #10 → #11) so the PII proxy and the honey tokens are already explained.

**Tags (5):** `AI`, `Compliance`, `SRE`, `Privacy`, `Open Source`.

Body tags: `PIPA`, `GDPR`, `Korea`, `LLM`, `DevOps`.

## Publishing checklist

- [ ] Proofread especially carefully — this one references real law
- [ ] Sanity-check the PIPA fine number (3% of domestic revenue per final amendment) before publish; pre-amendment drafts had 10%
- [ ] Verify `docs/DEPLOYMENT.md#tier-c` exists in repo before publishing
- [ ] Verify `docs/CONFIG.md` exists (may need to create as part of the OSS release)
- [ ] Include the Tier C architecture diagram as feature image
- [ ] Schedule Tue or Wed 9 AM ET
- [ ] Crosspost LinkedIn within 1 hour
- [ ] Pin LinkedIn for 2 weeks (this is the career-defining piece for Canadian recruiters)

## Cross-references

- Predecessors: Article #9 (PII proxy), Article #10 (honey tokens + kill switch)
- Successor: Article #8 (Open-Sourcing Aegis capstone)
- Source code references:
  - `apps/ai-engine/proxy/` — Layer 0.1
  - `apps/ai-engine/killswitch/` — Layer 0.3
  - `apps/ai-engine/llm_router/` — Layer 0.4
  - `apps/ai-engine/telemetry/` — Layer 0.5
  - `apps/ai-engine/honeytokens/` — Layer 0.6
  - `deploy/iam/aws/readonly-policy.json` — Layer 0.2
  - `docs/DEPLOYMENT.md` — Tier C guide

## Notes

- **Not legal advice.** Article is explicit about this. Engineering writeup, not a compliance opinion.
- Fine number: 3% of domestic revenue per the final amendment. Early drafts had 10%. Verify at publication time.
- No specific employer deployment details named. Describes the shape of a Tier C deployment in generic terms that happen to match how I'd deploy it at work — a legitimate OSS-user-case-study framing.
- Deliberately avoids making claims I cannot support with repo features.
