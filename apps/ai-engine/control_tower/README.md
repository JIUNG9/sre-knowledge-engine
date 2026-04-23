# Aegis Control Tower — Layer 3

The control tower is the brain of Aegis. It ties together every other
layer into a single end-to-end incident investigation loop.

## Three modes

| Mode | Preferred model | Context budget | LLM calls | Extras |
|------|-----------------|----------------|-----------|--------|
| `eco`      | Haiku-class  | ~4k tokens  | 1 | Wiki only, no telemetry |
| `standard` | Sonnet-class | ~16k tokens | 2 | Wiki + logs + metrics + alert history |
| `deep`     | Opus-class   | ~64k tokens | 3 | Everything + traces + Layer 2B pattern analyzer |

The mode dictates three things: the preferred model, the size of the
context bundle the `ContextBuilder` assembles, and how many reasoning
passes the orchestrator is allowed to run.

## How context is built

`ContextBuilder.build(alert, mode, budget_tokens=...)` pulls from the
layers Aegis already ships:

1. **Layer 1 wiki** — `WikiAdapter.query(topic)` surfaces the pages
   most relevant to the alert's service (substring ranking over the
   vault).
2. **Layer 2 SigNoz connectors** — `LogFetcher`, `MetricFetcher`,
   `TraceFetcher`, `AlertFetcher` return recent evidence from the
   observability plane.
3. **Layer 2B pattern analyzer** (deep mode only) — runs the collected
   log events through `PatternAnalyzer.analyze(...)` and attaches the
   markdown summary to the context.

Every fetcher is optional. A missing fetcher disables that data
source; it never crashes the investigation. Exceptions are caught and
downgraded to context notes. The builder enforces the mode's token
budget by trimming the largest contributors first (logs, traces) so
the wiki + metric signals survive.

## How actions flow through guardrails

Claude is prompted to respond with a single JSON object. When that
object contains a `proposed_action`, the orchestrator converts it to a
`guardrails.risk.Action`, hands it to
`GuardrailsEngine.evaluate(action, context, requested_tier)`, and
renders the resulting `GuardrailDecision` as a
`control_tower.ProposedAction` with the tier the action is actually
permitted to run at, any approvals still required, and a
human-readable explanation.

If guardrails deny, the action is downgraded to `SUGGEST` and the
reasons are surfaced. The control tower NEVER returns a raw action
— everything goes through the ladder.

## Kill switch

Before anything else, `investigate()` calls `killswitch.is_active()`.
When tripped, the function returns an `Investigation` with
`mode="halted"` and no action, `halted_reason="killswitch_active"`.
No LLM calls are made. No tools are invoked.

## Telemetry

Every call to `investigate()` starts an `aegis.investigation` OTel
root span. Each LLM call inside that span is wrapped with
`trace_llm_call` (GenAI semconv). Tool invocations — if any — use
`trace_mcp_tool`. When OTel is not installed, the wrapping becomes a
no-op so the tower still runs cleanly in minimal deployments.

## Example

```python
from control_tower import Alert, ControlTower, ControlTowerConfig

tower = ControlTower(
    llm_router=router,                 # from llm_router
    wiki=wiki_adapter,                 # WikiAdapter(WikiEngine(...))
    log_fetcher=log_fetcher,           # from connectors
    metric_fetcher=metric_fetcher,
    trace_fetcher=trace_fetcher,
    alert_fetcher=alert_fetcher,
    pattern_analyzer=PatternAnalyzer(),
    guardrails=guardrails_engine,      # from guardrails
    killswitch=killswitch,             # from killswitch
    config=ControlTowerConfig(default_mode="standard"),
)

investigation = await tower.investigate(
    Alert(
        service="payment-svc",
        severity="critical",
        title="error rate 5xx > 2% for 5m",
        environment="prod",
    ),
    mode="standard",
)

print(investigation.summary)
for hypothesis in investigation.hypotheses:
    print("-", hypothesis.title, hypothesis.confidence)

if investigation.proposed_action:
    pa = investigation.proposed_action
    print(f"{pa.name} -> {pa.tier} (approved={pa.approved})")
```

## FastAPI router

`control_tower.api.control_tower_router` exposes:

* `POST /api/v1/investigate` — body = `{"alert": {...}, "mode": "..."}`
* `GET /api/v1/investigations/{id}` — look up a previous run
* `GET /api/v1/modes` — list modes and their specs

The router depends on `get_control_tower` which, by default, raises
503. The app entry point overrides that dependency via
`app.dependency_overrides[get_control_tower] = lambda: tower` once
the tower is wired up. Intentionally not mounted from `main.py` yet
— that wiring ships in a follow-up PR.
