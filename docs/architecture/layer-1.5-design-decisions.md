# Layer 1.5 / 1.6 — Design Decisions for Review

> Companion to `layer-1.5-state-subscription.md` (the spec). This file
> records the non-obvious choices that landed during implementation,
> so a reviewer can challenge them without having to reverse-engineer
> intent from diffs.

---

## 1. Two flags collapse to one switch

The design doc names a single Phase-2 flag, `aegis.invalidation.write_frontmatter`. The implementation exposes **two** environment variables but uses them as one effective switch:

```
AEGIS_INVALIDATION_ENABLED            master kill switch (off)
AEGIS_INVALIDATION_WRITE_FRONTMATTER  shadow → live          (off)
```

Internally:
```python
engine = InvalidationEngine(
    shadow_mode = not settings.invalidation_write_frontmatter,
    ...
)
```

**Why two flags, not one:** The master switch keeps the entire CDC plane out of `main.py`'s lifespan when the operator hasn't reviewed the rollout yet — even one warning log per startup ("kubernetes client not installed") is noise on dev laptops and CI runs. The second flag is the design-doc semantic: shadow vs. write. Default-both-off is the safe state; the operator opts in twice, deliberately.

**Trade-off:** An operator can technically set `ENABLED=1, WRITE_FRONTMATTER=1` on day one and skip shadow mode. We considered enforcing two-week shadow mode in code; rejected it as patronizing. The audit log makes the rollout reviewable; we trust the operator to read it before flipping.

## 2. `shadow_mode` is the inverse of `write_frontmatter`

The design doc talks about a "write_frontmatter" flag; the engine constructor takes `shadow_mode`. We could have made these match. We didn't.

**Why:** `shadow_mode=True` reads in code as "this is a canary, don't mutate." `write_frontmatter=False` reads in env vars as "I haven't decided to go live yet." Both are correct from their respective vantage points. The `not` adapter at the boundary is one line; the alternative is awkward double-negative phrasing in either layer.

## 3. The factory returns `(engine, list[Task])` instead of a registry object

Existing subsystems (Control Tower, Scheduler, Executor) each return one object that lifespan stashes on `app.state`. Invalidation returns a tuple.

**Why:** The engine is one thing — a singleton with API. Consumer tasks are zero-or-many — k8s today, Terraform later, ArgoCD later. A single registry object would either grow ad-hoc methods or expose internals. The tuple is honest about what's being returned: the durable component plus a (possibly empty) list of supervised tasks the lifespan must cancel on shutdown.

**Trade-off:** When TerraformConsumer + ArgoCDConsumer land in Phase 3/4, the factory will keep returning a list. If task supervision becomes complex enough to need its own object, refactor at that point — premature now.

## 4. Engine runs even with zero consumers

The factory returns an engine even when k8s is disabled or unavailable. The engine has no events to drain, and the consumer task list is empty.

**Why:** API endpoints can still inject events (a later Phase-3 admin tool, replay from the audit log, manual incident triage). The engine without consumers is a no-op — no cost, no risk, full surface area. Killing it just because k8s isn't available would couple the engine's lifecycle to the consumer's, which is the wrong direction (consumers come and go; the engine is the integration point).

## 5. Per-slug `_last_seen` lives in process memory

Concurrent-edit detection compares an in-memory `dict[str, datetime]` against on-disk `last_updated`. After a process restart, this dict is empty.

**Why:** A restart-clear is *correct behavior*. If the engine just restarted, the last "us writing" event was lost from memory anyway; there's no useful "last_seen" to compare against. The first event after restart triggers a normal write (no false-positive conflict because `last_seen is None` short-circuits the check). Subsequent events use the now-populated dict.

**Trade-off:** A human edit that lands precisely between the engine's first-after-restart write and the next event will be silently overwritten. Mitigation: the daily reconciliation pass (Phase 3, not yet built) re-syncs everything. Until then, this is a documented edge case.

## 6. Atomic writes use POSIX `os.replace`, not `Path.write_text` + `os.fsync`

```python
fd, tmp_path = tempfile.mkstemp(prefix=..., dir=target.parent)
with os.fdopen(fd, "w") as f:
    f.write(content); f.flush(); os.fsync(f.fileno())
os.replace(tmp_path, target)
```

**Why:** The simpler `Path.write_text` is non-atomic — a crash mid-write leaves a torn frontmatter file that the next `frontmatter.load()` fails on. `os.replace` is the POSIX rename-into-place primitive: readers either see the old file or the new one, never a half-file. The tempfile must live in the same directory as the target so the rename stays on the same filesystem (cross-fs `os.replace` is not atomic).

**Cost:** One extra `fsync` per write. Negligible at our event rates; if rates ever climb to where this matters we'd batch writes per page anyway, not weaken the durability guarantee.

## 7. Resynth queue is append-only flat text, not a database

```
<vault_root>/_meta/resynth-queue.txt
```

Each line is one slug. Engine appends. Scheduler reads, dedupes, re-synthesizes, then truncates.

**Why:** Filesystem-first matches the rest of Layer 1.6 — the audit log is JSONL, the wiki is markdown frontmatter. A SQLite would be one more thing for operators to back up, one more shape for tests to mock. `grep` against `resynth-queue.txt` during an incident answers "what's about to be re-synthesized" in zero seconds. The dedup-and-truncate cost is bounded by the queue's growth rate, which the fanout cap keeps tame.

**Trade-off:** Concurrent writers in a multi-process deployment would race. We're explicitly single-process for the engine; the design doc calls this out.

## 8. The fanout cap engages on slug-count, not byte-size

```python
all_affected = sorted(slugs)
truncated = len(all_affected) > self.fanout_cap
affected = all_affected[: self.fanout_cap]
```

**Why:** Slug count maps directly to file rewrites, which is the cost we're capping. Byte size of the page contents is irrelevant — the engine doesn't read the body, just edits frontmatter. Sorted slice is deterministic so a replay marks the same prefix.

**Trade-off:** A single artifact with a 10K-page fanout will leave 9K pages stale until reconciliation sweeps them. That's a real gap. We accept it because the alternative (no cap) is worse: the engine stalls under burst load and stops processing later events. Reconciliation is a 24h SLA; for that 24h, the fanout-truncated pages are no worse than they were under Layer 1's pure decay model.

## 9. Read-only self-check fails closed, fails loud

```python
if self._can_i(auth_api, "create", "deployments", "apps"):
    raise PermissionError(...)
```

**Why:** A misconfigured (Cluster)Role granting write verbs is an operational fault that the consumer can detect at startup. We refuse to start. Logging a warning and proceeding would defeat the safety net — the operator might not see the warning until after a damaging operation. Crashing on startup forces them to fix the role.

**Why we don't fail closed when AuthorizationV1Api is absent:** Some dev clusters / minimal kubeconfig setups don't expose the authorization API at all. Refusing to start there punishes the developer for the deployment env's choices. We log a warning and proceed; the consumer's actual code paths are read-only by construction (no `create_*` / `update_*` / `delete_*` calls anywhere) so the fallback is safe. The self-check is a *redundant* guard, not the only guard.

## 10. K8s consumer is *disabled* by default at the env level

`AEGIS_INVALIDATION_K8S_DISABLED=true` (default).

**Why:** The ai-engine commonly runs on dev laptops, in CI, and in tests. Without this knob, every boot would emit a `ConsumerUnavailable` warning ("no kubeconfig found, no in-cluster config") that operators learn to filter and then miss when it actually matters. Default-disabled keeps boot logs clean. Cluster deployments flip it via Helm chart values; the value is exactly one Helm template line.

**Trade-off:** A new operator who *wants* k8s subscription on day one has to read the doc to find this flag. The doc is short; the flag name is self-explanatory. Acceptable.

---

## What's deliberately NOT in this branch

- **Prometheus metrics** (`aegis_consumer_events_total`, etc.) — design doc §4. Worth shipping as a small follow-up; didn't fit the time budget.
- **Daily reconciliation pass** — design doc §5. Phase 3 work; closes the event-loss window. Pending.
- **Scheduler-side resynth-queue consumer** — we write the queue; nothing reads it yet. The scheduler will read it next.
- **TerraformConsumer / ArgoCDConsumer** — Phase 3 / 4 per migration plan.

These are all explicitly deferred per the design doc's phased rollout. The branch is a complete Phase-2 alpha: schema additions + state subscription + invalidation engine + read-only self-check + lifespan wiring + dual-flag rollout. The flags default off, so merging this branch changes nothing in production until an operator opts in.
