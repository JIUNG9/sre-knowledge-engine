# Layer 1.5 State Subscription and Layer 1.6 Invalidation Engine

Subscribe to live infra state, treat the Aegis wiki as a materialized view, and invalidate page-level claims when their underlying justifications change.

**Status:** Draft 2026-04-26
**Author:** `<author>`

## 1. Problem statement

Aegis Layer 1 produces an LLM-synthesized wiki by reading from heterogeneous sources (Confluence exports, runbooks, SigNoz incident reports) and writing Obsidian markdown pages with YAML frontmatter. Each page has a `freshness` field, today one of `current`, `stale`, `archived`, `needs_review`, set at synthesis time and aged by the `StalenessLinter`. That linter operates at the source-type granularity, a runbook decays after N days, an incident report decays faster, etc. This is a coarse approximation. It misses two real failure modes that show up in production use.

The first failure mode is config drift. A page might assert "the auth-service runs on 6 replicas with a 512Mi memory request." That claim was true at synthesis time because some Terraform module or k8s `Deployment` manifest said so. When somebody scales the deployment to 12 replicas or bumps the memory request, the page is wrong, but no source-type clock has ticked. The wiki silently disagrees with the cluster. An on-call engineer reading the page during an incident is now operating from a stale projection. The decay model does not catch this because it cannot observe configuration changes; it only observes the calendar.

The second failure mode is more subtle and was first articulated by Jai Jalan reviewing earlier Aegis builds. Resolved-incident claims are overfit to their training distribution. An incident postmortem from 2024-03-15 saying "OOM in auth-service at 14:23, root cause was a leaked goroutine in the session middleware" is high-trust within the exact scope it describes (this service, this error signature, this code path). It is low-trust as a generalization to "any OOM in any service is a leaked goroutine." The current wiki does not represent this distinction. The agent that consults the wiki at query time treats every claim as universally applicable, then misapplies a tightly-scoped postmortem to an unrelated incident.

Source-type decay cannot fix either failure. Decay is a function of one variable (time), and these are functions of two variables (the state of an external artifact, the context of a query). The fix is to make claims dependency-aware and scope-aware. Layer 1.5 brings live infra state into the system as a stream of events. Layer 1.6 maintains a reverse index from infra artifacts to wiki claims and invalidates dependents when justifications change. Together they upgrade Aegis from a read-once snapshot to a continuously-revalidated knowledge base.

## 2. CS framing

The right way to read the wiki is as a materialized view over a non-SQL source of truth. The source of truth is the union of live infra state (k8s api objects, Terraform state, ArgoCD applications, cloud-provider APIs, source files in version control). The wiki is a derived projection over that state plus prior incident records. Stale wiki pages are stale views.

Once you accept that frame, two named patterns drop out.

**Change Data Capture (CDC).** In database replication, CDC subscribes a downstream system to the upstream's change log and propagates row-level deltas. The classic implementation reads the WAL or a binlog. The pattern generalizes to any system that emits ordered change events. Kubernetes already exposes this through `watch` semantics on the api server, which streams `ADDED`, `MODIFIED`, `DELETED` events with resource versions. Terraform's remote state file is a snapshot, not a stream, so we polyfill CDC by polling and diffing. ArgoCD has a webhook surface and a polled list. Layer 1.5 is the CDC ingest plane.

**Truth Maintenance System (TMS, Doyle 1979).** A TMS records each derived belief together with its justifications. When a justification's truth value changes, the TMS recomputes the status of beliefs that depended on it. A justification-based TMS (JTMS) is the variant we want. Each wiki page becomes a derived belief; its `config_dependencies` field is the justification list; the InvalidationEngine is the propagator. We do not need full ATMS-style multiple-context reasoning. Single-context JTMS is enough.

The combination of CDC plus TMS is also expressible in the event-sourcing vocabulary popularized by Greg Young, 2010. Live infra emits events. The wiki is a projection. Invalidation is a projection update. CQRS is the larger umbrella: writes go to the source of truth (operators, Terraform applies, ArgoCD syncs); reads go to the projection (the wiki, queried by the agent). We do not need full CQRS plumbing. We do need its discipline about who owns what.

A third frame, useful for the reverse-index design, is incremental view maintenance (Gupta and Mumick, 1995, "Maintenance of Materialized Views: Problems, Techniques, and Applications"). IVM asks: given a view defined by some query, how do we update it on each base-relation change without recomputing from scratch? The Aegis answer is: we don't try to recompute the page automatically. We mark it `pending_revalidation` and let the next scheduler tick re-synthesize using the LLM. This is a hybrid: the dependency tracking is IVM-shaped, the recomputation is deferred to a batch process because LLM calls are expensive.

The scope-of-applicability problem from section 1 maps to a different pattern. A claim with `scope.specific_to = {service: auth-service, error: OOM}` should match queries that fall inside that scope, and be demoted for queries that fall outside it. This is type-bounded dispatch in information retrieval, the same shape as multimethod dispatch in CLOS or trait selection in Rust. The query carries a context dict; the wiki dispatches retrieval based on which scopes it overlaps.

We do not invent vocabulary. We call CDC CDC, TMS TMS, IVM IVM. Reviewers reading this doc cold should be able to look up each pattern by its canonical name.

## 3. Schema additions

Two new optional fields on `WikiPage`, plus one new value in the `Freshness` literal. Both fields default to empty/None so existing pages, vaults, and tests continue to load without migration. YAML frontmatter serializes lists of Pydantic models naturally through the `frontmatter` library; round-tripping is verified by the existing `from_file` / `to_file` helpers in `wiki/synthesizer.py`.

```python
from pydantic import BaseModel, Field
from typing import Literal

ArtifactKind = Literal[
    "terraform", "k8s", "argocd", "cloud", "source_file"
]
GeneralizesTo = Literal["yes", "no", "with_conditions"]
Freshness = Literal[
    "current", "stale", "archived", "needs_review", "pending_revalidation"
]


class ConfigDependency(BaseModel):
    artifact_kind: ArtifactKind
    artifact_id: str  # e.g. "k8s:Deployment:auth-service"
    expected_value: str | None = None
    invalidate_on_change: bool = True


class ClaimScope(BaseModel):
    specific_to: dict[str, str] = Field(default_factory=dict)
    generalizes_to: GeneralizesTo = "no"
    generalizes_conditions: str | None = None
    trust_in_scope: float = Field(default=1.0, ge=0.0, le=1.0)
    trust_out_of_scope: float = Field(default=0.0, ge=0.0, le=1.0)


class WikiPage(BaseModel):
    # ... existing fields ...
    config_dependencies: list[ConfigDependency] = Field(default_factory=list)
    scope: ClaimScope | None = None
```

The `artifact_id` string is a structured but freeform identifier. The convention is `<kind>:<resource_type>:<name>` for k8s, `terraform:<module>.<resource>` for tf, `argocd:<app>` for ArgoCD apps. We do not enforce a parser yet; the InvalidationEngine treats it as an opaque key.

## 4. Layer 1.5: State Subscription

Layer 1.5 is the CDC ingest plane. It runs as a set of long-lived consumers that subscribe to upstream state and emit normalized `StateChangeEvent` records onto an in-process event bus. The InvalidationEngine in Layer 1.6 is the only subscriber on the bus today. Future consumers (audit log, drift dashboard) can subscribe later.

**Consumer protocol.** Each consumer is an async iterator of `StateChangeEvent`. The lifespan handler in `apps/ai-engine/main.py` starts each consumer as an `asyncio.Task` and supervises it. If a consumer task crashes, the supervisor logs the traceback, increments a counter, and waits a backoff before restarting. The invariant is that consumer crashes degrade the system to the no-CDC baseline, they do not break it. The wiki keeps serving stale pages, the StalenessLinter keeps decaying by source-type, the operator gets paged.

```python
from typing import AsyncIterator, Protocol
from pydantic import BaseModel
from datetime import datetime

class StateChangeEvent(BaseModel):
    artifact_id: str
    kind: ArtifactKind
    old_value: dict | None
    new_value: dict | None
    observed_at: datetime
    source: str  # consumer name, for logs and metrics

class Consumer(Protocol):
    name: str
    def stream(self) -> AsyncIterator[StateChangeEvent]: ...
```

**KubernetesConsumer.** Wraps the official `kubernetes` python client's `watch.Watch().stream()`. Subscribes to `Deployment`, `StatefulSet`, `ConfigMap`, `Secret` (metadata only, never `data`), and `HorizontalPodAutoscaler` across namespaces the service account can list. Reads only. The service account binds to a `ClusterRole` with `get,list,watch` verbs and nothing else. Each `MODIFIED` event yields one `StateChangeEvent` with `artifact_id="k8s:Deployment:auth-service"` shape and old/new values populated from the watcher's last-seen cache.

```python
from kubernetes import client, watch
import asyncio

class KubernetesConsumer:
    name = "k8s"

    def __init__(self, api: client.AppsV1Api):
        self.api = api
        self._cache: dict[str, dict] = {}

    async def stream(self) -> AsyncIterator[StateChangeEvent]:
        w = watch.Watch()
        loop = asyncio.get_running_loop()
        # The kubernetes client is sync; bridge with run_in_executor.
        # Each event yielded here is normalized into StateChangeEvent.
        ...
```

The watch loop needs care around resource version expiry. The api server returns `410 Gone` when the requested resource version has aged out of etcd's compaction window. The consumer handles that by relisting and resyncing the cache, then resuming the watch from the new version. This is the standard k8s informer pattern and is documented by the upstream client.

**TerraformConsumer.** Polls the remote state file. For S3 backends, it does a `HEAD` on the state object and compares ETags. When the ETag changes, it pulls the state, parses the `resources` array, and diffs against the previous parse. Each changed `resource.address` becomes a `StateChangeEvent` with `artifact_id="terraform:module.foo.aws_eks_cluster.main"` shape. Polling cadence defaults to 5 minutes, configurable. This is much lower frequency than k8s, which matches reality, Terraform applies are infrequent and human-driven.

We accept that polling has a detection lag. The reconciliation pass in Layer 1.6 closes the gap on the long tail (see section 5). For local-state development, the consumer can fall back to filesystem `mtime` polling. AWS account placeholder for documentation: `123456789012`.

**ArgoCDConsumer.** Two modes. Default mode polls `argocd app list -o json` every minute and diffs `status.sync.status` and `status.health.status`. The richer mode subscribes to ArgoCD's webhook stream when the deployment exposes one. ArgoCD applications carry their own dependency graph (sync waves, hook hooks), but for invalidation we treat the application as the artifact. `artifact_id="argocd:auth-service"` covers the common case.

**Failure mode.** Each consumer is independent. A misconfigured ArgoCD endpoint should not stop the k8s consumer from emitting events. The supervisor restarts each task with exponential backoff capped at 5 minutes. Consumers expose Prometheus metrics, `aegis_consumer_events_total{consumer=...}`, `aegis_consumer_errors_total`, `aegis_consumer_last_event_seconds`. Alerting on `last_event_seconds` catches silent failures.

**Wiring.** Consumers register with the `InvalidationEngine`. Registration is explicit, the engine's `register_consumer(consumer)` method spawns the supervised task and pipes events into its handler. There is no auto-discovery. Tests replace consumers with fixtures that yield canned events.

## 5. Layer 1.6: Invalidation Engine

Layer 1.6 takes the event stream from 1.5 and updates the wiki's freshness state. It is a small, focused component, three responsibilities: maintain the reverse index, handle events, append to the audit log.

**Reverse index.** A `dict[str, set[str]]` mapping `artifact_id` to the set of wiki page slugs that declared a dependency on it. The index is built at vault-load time by walking the vault directory and reading each page's `config_dependencies`. Build is O(N) in pages; lookup is O(1) per event. The index is held in memory. It is read-mostly: lookups happen on every event (high frequency), rebuilds happen on vault reload or on schema migration (low frequency). An `asyncio.Lock` guards writes; reads use the underlying dict directly because Python's GIL makes single-key reads safe.

```python
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

class InvalidationEngine:
    def __init__(self, vault: Path, log_path: Path):
        self.vault = vault
        self.log_path = log_path
        self._index: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def build_index(self) -> None:
        index: dict[str, set[str]] = {}
        for page_path in self.vault.rglob("*.md"):
            page = WikiPage.from_file(page_path)
            for dep in page.config_dependencies:
                index.setdefault(dep.artifact_id, set()).add(page.slug)
        async with self._lock:
            self._index = index

    async def handle_event(self, event: StateChangeEvent) -> None:
        slugs = self._index.get(event.artifact_id, set())
        if not slugs:
            return
        affected: list[str] = []
        for slug in slugs:
            page = self._load(slug)
            page.freshness = "pending_revalidation"
            self._save(page)
            affected.append(slug)
        self._append_log(event, affected)
        # Hint the next scheduler tick to re-synthesize these slugs.
        self._enqueue_resynth(affected)
```

**handle_event walkthrough.** First, look up dependent slugs in the reverse index. If empty, no-op (the common case for unregistered artifacts). Otherwise, for each slug: load the page, set `freshness = "pending_revalidation"`, write back to disk. Each frontmatter rewrite is a small atomic file operation; we use `tempfile` plus `os.replace` to avoid torn writes. Then append a single record to `_meta/invalidation-log.jsonl` capturing the timestamp, the full event, and the affected slugs. JSONL is append-only and grep-friendly. Finally, the engine emits a re-synthesis hint by writing the affected slugs to a queue file the scheduler reads on its next tick.

**Reconciliation.** A daily scheduler job re-walks the vault, rebuilds the dep index from frontmatter (defending against in-memory drift), and re-syncs k8s and Terraform state to detect events that the consumers missed. The reconciler holds the engine lock briefly for the swap, then runs a wide diff: for each artifact in the freshly-loaded state, if the in-memory `last_seen` value differs from the live value, synthesize a synthetic `StateChangeEvent` and feed it through `handle_event`. This closes event-loss windows, restart races during deploys, watch resource-version expiry, ArgoCD webhook drops. Reconciliation makes the system eventually consistent within a day even when CDC fails silently.

**Concurrency.** Writes to the index are batched per event burst. The supervisor groups events that arrive within a 100ms window into a single critical section. This avoids fanning out N file rewrites for a config map that flapped six times in a second. Reads of `self._index` happen without the lock; updates rebuild the dict and swap atomically. Writes to disk are serialized per page, two events on the same page within the burst window collapse to one rewrite.

**Cycle detection.** A claim can in principle invalidate a claim that, transitively, invalidates the first one. We bound the propagation: each `handle_event` call processes one level of the dependency graph. If we add claim-to-claim dependencies later (currently we only have artifact-to-claim), we add a one-pass-per-event budget and a cycle log. Today, page-level dependencies on external artifacts cannot cycle by construction.

**No DB.** The index lives in memory and is rebuilt from frontmatter on startup. The audit log is a JSONL file. No new persistence layer. This matches Aegis's filesystem-first posture.

## 6. Scope-of-applicability checks at query time

The agent queries the wiki for context, "what do we know about service=auth-service, error=OOM?" The wiki today returns matching pages by topic and trusts the agent to use them appropriately. With `ClaimScope`, retrieval becomes scope-aware.

The new API:

```python
class WikiQuery:
    async def query(
        self,
        context: dict[str, str],
        topic: str | None = None,
    ) -> list[tuple[WikiPage, float]]:
        """Return pages with a per-page applicability score in [0, 1]."""
```

The scoring rule is type-bounded dispatch. For each candidate page:

1. If `page.scope is None`, treat it as universally applicable, score = 1.0 (this is the legacy behavior, preserved by default).
2. If `page.scope.specific_to` is a subset of `context` (every key/value in `specific_to` is matched by `context`), the page is in-scope, score = `trust_in_scope`.
3. If `specific_to` and `context` overlap on at least one key but disagree on a value, the page is out-of-scope, score = `trust_out_of_scope`.
4. If they share no keys, the page is unrelated to this context dimension, fall through to topic-only relevance.

`generalizes_to = "with_conditions"` is a hint to the agent: the body contains a "this generalizes only when X" caveat, prefer to surface it. The retrieval layer does not parse the condition itself; it passes `generalizes_conditions` to the agent verbatim.

The point is not to hide pages from the agent. It is to demote them numerically so that an in-scope, high-trust postmortem outranks an out-of-scope, generalization-risky one. Synthesis at write time is what populates `scope`, the LLM is asked, "is this claim narrowly scoped or general?" and answers in structured form.

## 7. Failure modes and mitigations

**Event loss.** A consumer crashes mid-event. The watcher recovers from a stale resource version. A webhook payload is dropped by a flaky network. Any of these can result in a real change that produces no `StateChangeEvent`. Mitigation: the daily reconciliation pass in Layer 1.6 re-syncs the full state and synthesizes events for any artifact whose live value disagrees with `last_seen`. Worst-case detection latency is one reconciliation interval (24h by default, tunable). Pages affected by a missed event are silently stale during that window, which is no worse than the current Layer 1 baseline. Adding a higher-frequency reconciliation tier (every hour for high-priority artifacts) is a future tuning knob, not MVP.

**Cyclic invalidation.** Today, dependencies go from artifacts to pages, never page to page. Cycles are structurally impossible. If we extend to claim-to-claim dependencies, two pages could mutually invalidate. Mitigation: per-event budget, each `handle_event` processes at most one dependency hop. Beyond that, accumulate the pending invalidations on a queue and process them on the next tick. Detect cycles by tracking the set of slugs touched by an event; if a slug appears twice within one propagation, log a warning and break. This bounds CPU and prevents thrash.

**Index inconsistency after schema migration.** A schema change to `ConfigDependency` (new field, renamed key) leaves on-disk frontmatter inconsistent with the in-memory model. Pydantic v2 will raise on load. Mitigation: lazy rebuild on first event after restart. The `from_file` parser tolerates extra/missing fields and defaults conservatively; a strict validator runs in a separate `migrate.py` script invoked on-demand. We do not block engine startup on schema strictness; we log mismatches and proceed with the best-effort parse.

**Claim-level vs page-level scope.** MVP scope and dependencies live on the page, not on individual claims within the page. A page with three paragraphs, two tightly scoped to one incident and one general, gets a single `scope` block and a single `freshness`. This loses precision. The right unit is the claim, but representing claims as first-class records means splitting pages into multi-record files or moving to a record store, which is a bigger change. We document this as a known limitation. Migration path is laid out in section 8 phase 4.

**Burst overload.** A massive Terraform apply touches 200 resources. The consumer fires 200 events; the engine fans them out to potentially thousands of pages. Mitigation: the 100ms batching window collapses bursts; rewrites are serialized per page; a hard cap on per-tick fanout (default 1000 page-writes) drops to a warning log if exceeded. The reconciliation pass picks up dropped writes on the next cycle.

**Read-only credentials drift.** A well-meaning operator grants the consumer's service account write verbs to "fix" something. Mitigation: a startup self-check runs `auth can-i create deployments` and refuses to start if it gets back `yes`. The consumer is read-only by construction; any other state is a misconfiguration we want to catch loudly.

**Wiki under git, concurrent edits.** A human edits a page in their editor at the same moment the engine rewrites frontmatter. Mitigation: the engine writes via `tempfile` + `os.replace` and reads `last_updated` first; if the on-disk `last_updated` is newer than the last-seen, log a conflict and retry on next event. Real merge logic is out of scope for MVP; the operator's edit wins.

## 8. Migration plan

**Phase 1: schema.** Ship `ConfigDependency`, `ClaimScope`, and the `pending_revalidation` freshness value as additive Pydantic changes. No reads or writes outside tests. Existing vaults load unchanged. Existing pages serialize the new fields as empty/null. This is a drop-in patch. Risk: low. Ship behind no flag; the absence of consumers means there is no behavior change.

**Phase 2: consumer plus engine, shadow mode.** Ship `KubernetesConsumer`, `InvalidationEngine`, the reverse index, the audit log. Run for two weeks with a feature flag, `aegis.invalidation.write_frontmatter`, defaulted off. Events flow, the index builds, the audit log fills. Frontmatter writes are gated behind the flag. The two-week observation period is for catching event-rate surprises (do we get 10 events/sec or 10 events/hour from a representative cluster?) and for tuning the burst window. Operator dashboards: events/sec, pages/event ratio, audit-log size growth.

**Phase 3: production invalidation.** Flip the flag. `pending_revalidation` starts appearing in real frontmatter. The next-tick re-synthesizer is wired up to consume the queue and ask the LLM to re-merge. Add `TerraformConsumer` once k8s is stable; tf events are lower-frequency and lower-risk so we add them once the engine has proven itself on the noisier source.

**Phase 4: ArgoCD plus claim-level scope.** Ship `ArgoCDConsumer`. Begin the larger refactor that splits pages into multi-claim records, each with its own scope and dependencies. This is where the page-level limitation called out in section 7 gets resolved. Phase 4 is its own design doc; do not block on it.

Each phase ships independently and is reversible. Removing a consumer is a config change. Removing the engine returns the system to Layer 1 baseline. The schema additions in Phase 1 are forward-compatible by design.

## 9. Test plan

**Unit.** `Consumer` interface conformance, a parametrized test that all registered consumers expose `name` and an async `stream()` method, never block, and emit valid `StateChangeEvent` records. `InvalidationEngine.handle_event` fan-out logic with a synthetic index and a tmp vault, assert that `freshness` flips, that the audit log gains exactly one record, that unrelated pages are untouched. Reverse-index build correctness, property-based tests with `hypothesis` over generated `WikiPage` lists, assert the index is the inverse of the dependency relation.

**Integration.** The Aegis convention is `mock_server.py` per source, a small aiohttp server that mimics the upstream protocol. We add `mock_kube_apiserver.py` that serves a watch stream over a fixture YAML of resources. Tests start the mock, point a real `KubernetesConsumer` at it, push a sequence of `MODIFIED` events through the watch, and assert that the engine picks them up and rewrites the right pages. Mock the Terraform backend with a localstack S3 plus a hand-edited statefile. Mock ArgoCD with a static JSON server.

**End-to-end.** A scenario test that loads a pre-built vault with three pages, page A depends on `k8s:Deployment:auth-service`, page B is unrelated, page C has scope `{service: auth-service}`. Push a single k8s `MODIFIED` event for `auth-service`. Assert: page A flips to `pending_revalidation`, page B unchanged, page C unchanged (scope is read-time, not write-time). Run one scheduler tick, assert page A is re-synthesized and back to `current`. The scenario runs in CI in under a minute against the mock server fleet.

**Regression.** Before merging, a benchmark records events/sec sustained throughput under a synthetic load (1000 events/min for 10 minutes). The engine must not exceed 200MB resident memory, the audit log must not exceed 100MB on disk, and per-event handling latency p99 must stay under 50ms. These thresholds are conservative starting points and tunable.

## 10. Open questions

A few things this doc deliberately defers, listed here so the next session can pick them up.

1. Reconciliation cadence per artifact kind. 24h is a reasonable default for the long tail; high-priority artifacts (production EKS clusters, top-traffic services) probably want faster. Where does the priority signal come from?

2. Re-synthesis cost control. The next scheduler tick re-merges every `pending_revalidation` page. Under burst load that is a lot of LLM calls. Do we coalesce, batch, or rate-limit at the LLM client?

3. Claim-level granularity, the Phase 4 question. Multi-claim records per page, or one file per claim? File-per-claim is simpler but explodes vault size.

4. Should the audit log be queryable through the existing `routers/wiki.py` endpoints, or kept as a flat file? The flat file is fine for forensics today; a queryable surface helps the operator dashboard.

5. How do `expected_value` mismatches surface? Today we only flag on change; we could also flag on "current value differs from declared expected value at synthesis time."
