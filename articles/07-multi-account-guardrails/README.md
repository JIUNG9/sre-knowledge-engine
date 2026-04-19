# Article 07 — "Production Guardrails for AI Agents: The Risk Tier System Across 4 AWS Accounts"

**Series:** Aegis v4.0 — Part 7 of 8
**Author:** June Gu
**Target length:** 3,000-3,400 words
**Status:** Draft — ready for Medium publishing
**Layer referenced:** Layer 4 (Guardrails — PLANNED)

## Content summary

A deep dive on how Aegis's Layer 4 Guardrails let an AI act in a multi-account AWS hub-spoke environment without introducing risk. Covers: the topology (anonymized — 1 hub, 3 spokes, 1 security account, IDs `111111111111` through `555555555555`), a 20-row risk classification table with AWS-specific examples (CloudWatch, kubectl, Terraform, IAM, S3, KMS), account-scope adjustments (hub becomes HIGH, security becomes BLOCKED), pre-validation (dry-run + IAM simulator + OPA), post-validation with auto-rollback, the hard-coded "AI can't touch IAM" rule (three defense layers), SOC2-compliant per-account audit trail, rollback-first policy, a timeline example (13-second mitigation), and the trust-building automation ladder (observe -> recommend -> low-auto -> full-auto).

## Tags

`AI` `Security` `AWS` `SRE` `DevSecOps` `Compliance`

## Publishing checklist

- [ ] Scrub check passed (no real account IDs, no real INC-###, no internal paths)
- [ ] Medium import: copy `article.md`; verify table rendering
- [ ] Header image: risk tier matrix visualization (to generate)
- [ ] Canonical URL set to Medium URL after publish
- [ ] Cross-post to Dev.to with `canonical_url`
- [ ] Add to Aegis repo README "Articles" section with link

## LinkedIn forward reference

Short-form LinkedIn post (to be drafted in `linkedin-posts/07-multi-account-guardrails.md`):
- Hook: "AI agents without guardrails are a production incident waiting to happen — especially across 4 AWS accounts."
- 3-bullet summary: 5-tier risk model + hub-spoke scoping + hard-coded IAM block
- CTA: link to Medium article + Aegis repo; ask audience what they've built for similar scenarios
- Tags: #AI #AWS #SRE #DevSecOps #Security
