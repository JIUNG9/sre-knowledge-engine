# Article 06 — "We Found That 80% of Our Incidents Happen on Monday 9 AM"

**Series:** Aegis v4.0 — Part 6 of 8
**Author:** June Gu
**Target length:** 2,600-3,000 words
**Status:** Draft — ready for Medium publishing
**Layer referenced:** Layer 2 (SigNoz Connector — PLANNED)

## Content summary

A data-driven narrative showing how 180 days of SigNoz alert history revealed an 80% clustering of firing incidents between Monday 09:00-11:00 KST. The article walks through: the informal pattern observation, the ClickHouse/SigNoz query that proved it, three real(istic) pattern types (auth cold-start, cron write amplification, overnight idle), the Aegis Layer 2 pattern-analyzer architecture (planned), and how patterns feed the Claude Control Tower for pre-positioning. Includes cost-savings table (~$3K/month overnight), Mermaid architecture + sequence diagrams, and a working ClickHouse query readers can run today.

## Tags

`SRE` `Observability` `AI` `Pattern Recognition` `DevOps` `FinOps`

## Publishing checklist

- [ ] Scrub check passed (no account IDs, no real INC-###, no internal paths)
- [ ] Medium import: copy `article.md` content; Medium renders Mermaid as image
- [ ] Header image: Monday-morning incident heatmap (to generate)
- [ ] Canonical URL set to Medium URL after publish
- [ ] Add to Aegis repo README "Articles" section with link
- [ ] Cross-post to Dev.to with `canonical_url` pointing to Medium

## LinkedIn forward reference

Short-form LinkedIn post (to be drafted in `linkedin-posts/06-monday-patterns.md`):
- Hook: "We looked at 6 months of incident data. 80% happened Mon 9-11 AM. It wasn't random."
- 3-bullet summary: login spike + cron amplification + batch deploys
- CTA: link to full Medium article + Aegis repo
- Tags: #SRE #Observability #AI #DevOps #FinOps
