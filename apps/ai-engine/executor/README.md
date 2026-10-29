# Aegis P2.5 — Layer 4 Executor

The executor is the keystone of Phase 2: it turns Aegis from an *advisory* AI SRE (proposes actions, humans run them) into a *self-healing* one (the agent runs the action under the 4-stage automation ladder, with every gate enforced in code).

## The five gates, in execution order

Over HTTP the caller never sends a decision. It sends the action and a `grant_id` (see [Approval grants](#approval-grants)); the executor rebuilds the decision from the grant it stored. In-process, when `Executor.execute(action, decision)` is called, every action passes through these gates in order. If any gate refuses, the action does not run and an audit record is written.

1. **Config gate.** If `ExecutorConfig.enabled=False`, refuse with `executor_disabled`.
2. **Tier gate.** Only `decision.tier == "EXECUTE"` proceeds. SUGGEST / DRAFT / PROPOSE all refuse with `not_approved_for_execution`.
3. **Approval gate.** The decision must be `approved=True` AND have at least `required_approvals` distinct approvers (default floor: 2 for EXECUTE).
4. **Verb / wrapper gate.** The action's verb is mapped to one of three wrappers (kubectl / terraform / aws). The verb must:
   - Not be in the wrapper's hard-coded `blocked_verbs` (e.g. `kubectl delete`, `terraform destroy`)
   - Be in the wrapper's `supported_verbs`
   - Be in the operator's `allowed_verbs[wrapper]` config
5. **Kill switch gate (last defense).** Even after every other gate has cleared, the kill switch is checked one final time at the moment of dispatch. This is intentional: the kill switch is the *last-mile* safety, not the first.

Only after all five gates clear does the executor invoke the wrapper.

## Approval grants

The code that runs the real approval gate (Slack, GitHub, CLI) calls `Executor.issue_grant(action, decision)` in-process. The executor checks the decision would clear the tier and approval gates, then stores a grant and returns its id. That id is all an HTTP caller gets.

Not wired yet: nothing in this repo calls `issue_grant` today, so `/execute` refuses every request with `grant_unknown_or_used`. Connecting the control tower's approval step (`control_tower/action.py`) to `issue_grant` is the next change.

| Property | How it's enforced |
|---|---|
| Bound to one action | The grant stores a SHA-256 digest of name, verb, target, environment, category, blast radius, reversible and metadata. Change any of them (say `metadata.replicas` from 3 to 0) and the grant is refused with `grant_action_mismatch`. |
| Short-lived | `AEGIS_EXECUTOR_GRANT_TTL_SECONDS`, default 900 (15 minutes). After that: `grant_expired`. |
| Single use | A real run removes the grant under a lock. The second call gets `grant_unknown_or_used`. `/dry-run` checks the grant without using it, so the operator can preview and then execute. |
| Distinct approvers | The same name twice counts once. |

Grant refusals go through the normal refusal path, so each one is audited and traced (`aegis.executor.gate=grant`).

The default `GrantStore` is in memory, which is right for one replica. Running several replicas needs a shared store with the same `issue` / `peek` / `consume` methods.

## Default verb allowlist

Conservative by design. Operators must explicitly extend this in `ExecutorConfig.allowed_verbs` to expand reach.

- **kubectl** — `scale`, `rollout-restart`, `get`, `describe`, `logs`. Permanently blocked: `apply`, `delete`, `patch`, `exec`, `cp`, `edit`, `replace`, `taint`.
- **terraform** — `plan` (always allowed); `apply` only when `terraform_apply_allowed=True` AND tier=EXECUTE AND ≥2 approvals. Permanently blocked: `destroy`, `import`, `state` (state mutations).
- **aws** — `describe-*`, `list-*`, `get-*` only. Mutating verbs are not loadable as wrapper inputs.

## How to enable

Disabled by default. Production deployments opt in:

```bash
export AEGIS_EXECUTOR_ENABLED=1            # master switch
export AEGIS_EXECUTOR_API_TOKEN=...        # required; from your secret store, not a literal
export AEGIS_EXECUTOR_DRY_RUN=0            # turn OFF dry-run (default is on)
export AEGIS_EXECUTOR_AUDIT_LOG=/var/log/aegis/executor-audit.jsonl
export AEGIS_EXECUTOR_TF_APPLY_ALLOWED=1   # explicit opt-in for terraform apply
```

Without `AEGIS_EXECUTOR_API_TOKEN` the executor is not attached and every route stays at 503.

Even when `AEGIS_EXECUTOR_ENABLED=1`, dry-run is on by default — the wrapper reports the argv it WOULD have invoked but does not invoke the binary. Set `AEGIS_EXECUTOR_DRY_RUN=0` to flip to real execution. This staged rollout is on purpose.

## API

`/api/v1/executor` — mounted unconditionally so OpenAPI surfaces the endpoints. The dependency returns 503 until the lifespan hook attaches a real `Executor` instance. Every route needs `Authorization: Bearer <AEGIS_EXECUTOR_API_TOKEN>`; otherwise 401.

- `POST /api/v1/executor/execute` — body: `ExecuteRequest(investigation_id, action, grant_id, dry_run)` → `ExecutionResult`. A body with a `decision` field is rejected (422). `dry_run: true` forces a preview; `dry_run: false` can't override `AEGIS_EXECUTOR_DRY_RUN=1`.
- `POST /api/v1/executor/dry-run` — same as execute, but forces `dry_run=True` and leaves the grant usable
- `GET /api/v1/executor/audit?since=ISO&limit=50` — paginated audit JSONL
- `GET /api/v1/executor/config` — current allowed verbs / dry-run mode / two-approval floor

## Audit trail

Every execution — refused or executed — produces:

1. One OTel span (`aegis.executor.execute`) with attributes for tier, verb, target, gate-that-stopped-it, dry-run, outcome, exit code, duration.
2. One JSONL line in `audit_log_path`. Default `./aegis-executor-audit.jsonl`. The line includes timestamp, investigation_id, action verb + target + tier, approvers, outcome, exit code, and **hashes** of stdout / stderr (not the raw bytes — so the audit log is safe to ship to a SIEM without leaking PII; the operator keeps the raw blobs under their own control).

If an audit write fails, the execution is refused. We never run an unaudited command.

## Adding a new wrapper

1. Subclass `executor.wrappers.base.Wrapper`. Define `name`, `binary`, `supported_verbs`, `blocked_verbs`, and `build_args(action) -> list[str]`.
2. Use `self.extract_verb(action)` to read the wrapper-relative verb (handles both `"<wrapper> <verb>"` and bare `"<verb>"` forms).
3. Register it in `Executor._default_wrappers` or pass via the `wrappers={...}` constructor argument.
4. Add a row in `ExecutorConfig.allowed_verbs` for the new wrapper.
5. Write a `tests/test_<name>.py` mirroring the existing wrapper tests.

## Testing

```bash
cd apps/ai-engine && pytest executor/tests
```

Tests cover: grant binding, expiry, single use under concurrency, bearer auth, the rejected client-supplied decision, tier refusals, approval refusals, kill-switch refusals, verb blocking, dry-run, exception isolation, audit append, idempotency, forbidden verbs (kubectl delete, terraform destroy, aws iam mutating). Tests that turn dry-run off use the `fake_binary` fixture, which replaces `subprocess.run`, so the suite never reaches a real cluster from a developer laptop.

## Related

- Layer 3 — Claude Control Tower (`apps/ai-engine/control_tower/`): produces the `ProposedAction` that the executor consumes.
- Layer 4 — Production Guardrails (`apps/ai-engine/guardrails/`): produces the `GuardrailDecision` that the executor uses to decide whether to dispatch.
- Layer 0.3 — Kill Switch (`apps/ai-engine/killswitch/`): checked once more at dispatch time.
- Layer 0.5 — OTel Tracing (`apps/ai-engine/telemetry/`): every gate emits a span attribute, every dispatch emits a full span.
