# LinkedIn — Article 7: Production Guardrails Across 4 Accounts

Three variants. Pick one. Each targets 1,300 characters. No emojis. CTA to Medium + GitHub.

---

## Variant A — Technical

**AI agents without production guardrails are a postmortem waiting to happen. Here is the risk tier system I built across a four-account AWS hub-spoke.**

Every action the agent proposes is classified before anything runs:

- None — read-only queries (logs, metrics, traces). No gate.
- Low — scale up, cache flush, non-prod config. Auto-approved with dry-run.
- Medium — pod restart, deployment rollback, scale down. Slack approval required.
- High — terraform apply, resource deletion. Human-only forever.
- Blocked — IAM modifications, cross-account role changes. Never automated.

Three more gates on top of the classifier:

Pre-validation — every action runs a dry-run first. If dry-run fails, action blocks with a reason.
Post-validation — after execution, metrics are re-checked against a baseline. If they did not improve, auto-rollback fires.
Audit trail — every decision lands in a SOC2-compliant JSON log with model, tokens, cost, risk, approver, dry-run result, metrics before and after.

The four-account split — shared services, prod, stage, dev — means blast radius is bounded by account even when the classifier is wrong.

Full write-up with the risk table and audit schema: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #AISafety #DevSecOps

---

## Variant B — Career

**I spent a year running multi-account AWS infrastructure. The lesson I took into Aegis is that blast radius is the only thing that matters.**

Four AWS accounts, hub-spoke topology, Transit Gateway between them. Terraform modules for everything. IAM with least-privilege by default. The architectural pattern was solid. The problem was that every new tool — observability agent, deployment system, security scanner — wanted broad permissions.

Aegis is designed the other way. The agent gets read-only by default. Write actions route through a risk classifier. Pre-validation dry-runs. Post-validation metric checks. Audit trails you could hand to a SOC2 auditor without translation. IAM modifications are blocked forever — no config flag can enable them.

Quality in infrastructure is the absence of surprises. Aegis encodes that.

I work as an SRE. Relocating to Canada in 2027. Hiring managers: happy to walk through this pattern in detail.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #AWS #PlatformEngineering

---

## Variant C — Hot take

**Every "AI for SRE" pitch this year conveniently skips the part where the agent can destroy your infrastructure.**

The demo shows an agent restarting a pod. The demo does not show the agent accidentally running kubectl delete against the wrong namespace, or terraform applying a destroy on a production RDS, or modifying an IAM role because the LLM got creative. Those failure modes are not hypothetical.

Aegis is built around the assumption that the agent will be wrong. Risk tiers gate every action. Dry-run before execute. Metric check after execute. Auto-rollback if metrics did not improve. IAM and resource deletion are permanently blocked — no setting can enable them. Four-account AWS split bounds blast radius regardless.

This is not optional tooling. This is the bar before "AI for SRE" deserves a production footprint.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#AI #SRE #AWS
