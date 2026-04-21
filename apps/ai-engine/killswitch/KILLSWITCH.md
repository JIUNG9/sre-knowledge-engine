# killswitch.md — Aegis Emergency Stop

Follows the [killswitch.md](https://killswitch.md) convention: a single,
unambiguous, operator-facing description of how to halt this system **right
now**.

## TL;DR — 3 ways to stop Aegis

### 1. `aegis panic` (preferred)

```bash
# Interactive — will prompt for operator + reason
aegis panic

# Non-interactive (PagerDuty webhook, CI, etc.)
aegis panic --force --operator pagerduty --reason "p0-db-outage-2026-04-21"

# Panic AND revoke AWS session
aegis panic --force --operator june.gu --reason "compromised-key" \
  --revoke-aws --aws-role-arn arn:aws:iam::123456789012:role/aegis-agent
```

Trips the kill switch, appends a structured event to `./aegis-audit.jsonl`,
and — if `--revoke-aws` is set — attaches the `AWSRevokeOlderSessions` inline
deny policy to the configured IAM role.

### 2. Redis CLI one-liner

If the `aegis` binary is unavailable (network partition, laptop dead) any
operator with Redis access can trip the switch directly:

```bash
redis-cli -u redis://aegis-redis:6379 SET aegis:killswitch 1
```

The agent will pick it up on the next tool invocation (sub-5ms check). To
clear:

```bash
redis-cli -u redis://aegis-redis:6379 DEL aegis:killswitch
```

> NOTE: the one-liner sets an *unstructured* value. `aegis status` will
> report `reason: "unstructured state value"` rather than a full operator +
> reason. Prefer `aegis panic` when you have shell access.

### 3. File-backend flag (no Redis)

If Redis is down, Aegis falls back automatically to a local flag file. To
trip the switch by hand on a single node:

```bash
echo '{"active": true, "reason": "redis-outage", "operator": "$(whoami)"}' \
  > ./aegis-killswitch.flag
```

Clear with `rm ./aegis-killswitch.flag`.

## Backends at a glance

| Backend | When it's used | Trip latency | Scope |
|---------|----------------|--------------|-------|
| `redis` (default) | Normal operation | < 5 ms read | Fleet-wide |
| `file` | Redis unreachable, or `AEGIS_KILLSWITCH_BACKEND=file` | single `stat()` | Single node |

Aegis automatically falls back from `redis` to `file` if the Redis client
cannot connect at startup. The fallback is logged and recorded in the audit
log (`event: backend_fallback`).

## What `aegis panic` does, step by step

1. Prompt for operator + reason (unless `--force`, in which case the flags
   are mandatory).
2. Write a structured state blob to Redis (or the flag file):
   `{active, reason, operator, tripped_at}`.
3. Append `{"event": "trip", "operator": ..., "reason": ..., "backend": ...}`
   to `./aegis-audit.jsonl`.
4. If `revoke_aws_on_panic` is enabled **and** `aws_role_arn` is set, attach
   the `AWSRevokeOlderSessions` deny policy to the role. This revokes *every*
   session token issued before the current timestamp.

## What it does NOT do

- It does **not** kill the FastAPI process — running investigations may
  continue their reasoning, but every MCP tool call (decorated with
  `killswitch_gate`) will raise `KillSwitchTripped` before side-effects.
- It does **not** revoke AWS credentials unless you explicitly opt in.

## Releasing the switch

```bash
aegis release --operator june.gu
# or, if Redis is the only option available:
redis-cli -u redis://aegis-redis:6379 DEL aegis:killswitch
```

Release events are also written to the audit log.

## Audit log location

All events land in `./aegis-audit.jsonl` by default. Override with
`AEGIS_KILLSWITCH_AUDIT_LOG_PATH`.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AEGIS_KILLSWITCH_REDIS_URL` | `redis://localhost:6379` | Redis connection. |
| `AEGIS_KILLSWITCH_BACKEND` | `redis` | `redis` or `file`. |
| `AEGIS_KILLSWITCH_REVOKE_AWS_ON_PANIC` | `false` | Opt-in AWS revoke. |
| `AEGIS_KILLSWITCH_AWS_ROLE_ARN` | — | Required when revoking. |
| `AEGIS_KILLSWITCH_STATE_KEY` | `aegis:killswitch` | Redis key name. |
| `AEGIS_KILLSWITCH_AUDIT_LOG_PATH` | `./aegis-audit.jsonl` | JSONL audit file. |
| `AEGIS_KILLSWITCH_FILE_BACKEND_PATH` | `./aegis-killswitch.flag` | File-backend flag. |
