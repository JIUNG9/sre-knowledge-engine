# Aegis Guardrails — Layer 4

Production guardrails for the Aegis AI SRE agent. Every action the agent
wants to take passes through the 4-rung **automation ladder**, a data-driven
policy engine, a pluggable approval gate, and an append-only audit log — in
that order, every time.

## The ladder

| Tier      | What happens                                                                            | Default approvals |
| --------- | --------------------------------------------------------------------------------------- | ----------------- |
| `SUGGEST` | Propose an action to a human; no side effects.                                          | 0                 |
| `DRAFT`   | Produce an artifact (ticket, PR comment, Slack draft) — do not transmit.                | 1                 |
| `PROPOSE` | Hit the dry-run / plan-only endpoint (`terraform plan`, `kubectl --dry-run=server`).    | 1                 |
| `EXECUTE` | Run the real action. Still subject to kill-switch + audit.                              | 2                 |

Ordering is monotonic: `SUGGEST < DRAFT < PROPOSE < EXECUTE`. Policies can
*downgrade* a requested tier but never silently upgrade it.

## The risk model

`RiskAssessment.assess` scores any `Action` in `[0, 100]`. It is additive and
fully explainable — every contribution ships with a human reason:

- **Environment** — `dev` (+5), `stage` (+20), `prod` (+40). Unknown → prod.
- **Category** — `iam` / `rbac` / `secrets` (+25–30), `db` (+20), `s3` (+15).
- **Destructive verb** — `delete` / `drop` / `scale-to-zero` → +25.
- **Blast radius** — log-ish bucket up to +25.
- **Reversibility** — irreversible → +10.
- **Caller extras** — any additional `(+n, reason)` tuples via context.

The score yields a **ladder cap** (`tier_cap_for_risk`). Policy rules tighten
from there — never loosen.

## Worked example — "scale deployment `payments` to 0 in prod"

```python
action = Action(
    name="scale deployment payments to 0",
    verb="scale-to-zero",
    target="deployment/payments",
    environment="prod",
    category="deployment",
    blast_radius=1,
)
decision = engine.evaluate(action, requested_tier=AutomationTier.EXECUTE)
```

1. **Risk**: `+40` prod, `+25` destructive = 65 → ladder cap **PROPOSE**.
2. **Policy**: `scale-to-zero-prod-block` fires → cap **DRAFT**;
   `prod-requires-two-approvals` fires → 2 approvers required.
3. **Effective tier**: `min(EXECUTE, PROPOSE, DRAFT)` = **DRAFT**.
4. **Approvals**: Slack gate posts to `#prod-oncall` and waits for 2 `:approve:`
   reactions. If < 2 → downgrade to `SUGGEST`.
5. **Kill switch**: only checked when returning `EXECUTE`; here we end at
   `DRAFT`, so the switch is a no-op this time.
6. **Audit**: one JSONL row — actor, risk score, reasons, approvers, outcome.

## Approval flow

| Gate                  | Backend   | Use it when…                         |
| --------------------- | --------- | ------------------------------------ |
| `NoneApprovalGate`    | `none`    | `SUGGEST` only — never anywhere else |
| `LocalCLIApprovalGate`| `cli`     | Demos / local dev                    |
| `SlackApprovalGate`   | `slack`   | Team-of-record lives in Slack        |
| `GithubApprovalGate`  | `github`  | Change flows through a PR            |

Gates are pluggable: implement `ApprovalGate.request(ApprovalRequest)` and
hand it to `GuardrailsEngine`.
