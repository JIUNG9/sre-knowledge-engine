# Aegis Cloud IAM — Read-Only Agent Identities

The Aegis AI agent must be **technically unable** to mutate cloud state. Not
"discouraged" — impossible. This directory ships drop-in IAM templates for
AWS, GCP, and Azure that enforce read-only access at the policy layer, so even
a compromised agent or prompt-injected LLM cannot delete, create, or modify
resources in your account.

## Design

Three defense layers, stacked:

1. **Explicit `Deny` beats any `Allow`** — The AWS managed policy uses
   wildcard denies on `*:Delete*`, `*:Create*`, `*:Put*`, `*:Update*`, `*:Modify*`,
   `*:Attach*`, `*:Detach*` across every service, plus full denies on
   `iam:*`, `secretsmanager:*`, `organizations:*`, and `ce:*` (Cost Explorer
   charges per API call). Explicit deny cannot be overridden by an identity
   or resource policy — this is the AWS IAM evaluation contract.
2. **Session policy intersection** — `session-policy-example.json` is applied
   at `sts:AssumeRole` time. Effective permissions are the **intersection** of
   the role policy and the session policy (see AWS SDK docs on `PolicyArns`
   in `AssumeRole`). Even if the base role drifts, the session stays tight.
3. **Trust policy with MFA + ExternalId** — The role can only be assumed when
   `aws:MultiFactorAuthPresent = true` and the caller presents the shared
   ExternalId. This blocks the classic confused-deputy attack described in
   the AWS blog *How to use Trust Policies with IAM Roles* and aligns with
   IAM Access Analyzer's public-access checks.

For GCP and Azure we use **custom roles with permission allowlists** (not
predefined Viewer roles, which are too broad — e.g., `roles/viewer` grants
`iam.serviceAccounts.actAs` indirectly on some projects).

## Validator

`validator.py` statically analyzes each JSON/YAML policy and fails CI if it
finds an `Allow` on any mutating verb, a missing high-risk deny, or an
over-broad resource scope. Run it pre-commit; run it in CI.

## References

- AWS Security Blog, *Techniques for writing least-privilege IAM policies*
- AWS docs, *IAM Access Analyzer policy validation*
- AWS blog, *NotAction with Deny in SCPs* (the pattern this adapts)
