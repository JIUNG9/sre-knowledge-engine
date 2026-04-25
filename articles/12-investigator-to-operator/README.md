# Article #12 — From Investigator to Operator: Wiring the Self-Healing Executor

**Status:** outline only. Will be drafted after Phase 2.5 (Layer 4 executor) ships.

## What this article will cover

Phase 2 of Aegis turns the agent from an investigator (says what's wrong, suggests what to do) into an operator (actually runs the fix under the 4-stage automation ladder). This article documents that leap.

The shape:

1. **The honest gap** — Layer 3 produces beautiful `ProposedAction` objects. Layer 4 correctly classifies whether they're EXECUTE-eligible. Nothing actually runs the kubectl/terraform/aws command. The ladder existed; the bottom rung was missing.
2. **Why we waited** — building the executor BEFORE the safety foundation (Layer 0) and the policy engine (Layer 4) would have been irresponsible. The order matters: investigate → propose → gate → execute, with safety wrapping every step.
3. **What the executor is** — `apps/ai-engine/executor/`. Reads `ProposedAction.tier`, validates approvals, dispatches via thin wrappers around kubectl/terraform/aws-cli, captures stdout/stderr, attaches `execution_result` to the `Investigation`, writes audit JSONL. Around 800 LoC.
4. **The three rules that keep it sane** — (a) no executor wrapper accepts arbitrary shell, only typed commands; (b) every wrapper has a dry-run mode tested in CI; (c) the kill switch is checked one last time at the moment of execute, after every other gate has cleared.
5. **The first 5 actions we autoprobe** — pod restart, deployment scale, log query, CloudWatch metric query, RDS describe. None of them mutating in ways that can't be reversed in under 60 seconds.
6. **What broke and what we learned** — to be filled in once we run it for a month.

## Source files this article will reference

- `apps/ai-engine/executor/__init__.py` (TBD)
- `apps/ai-engine/executor/dispatcher.py` (TBD)
- `apps/ai-engine/executor/wrappers/{kubectl,terraform,aws}.py` (TBD)
- `apps/ai-engine/executor/audit.py` (TBD)
- `apps/ai-engine/control_tower/orchestrator.py` (already shipped, will be edited to call executor)

## Estimated draft date

**July 2026**, after Phase 2.5 (executor) ships. Phase 2.5 is currently planned for late June.

## Tags (planned)

`AI`, `SRE`, `DevOps`, `Automation`, `Open Source`

## Related

- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) — Layer 3 + Layer 4 architecture
- [README.md](../../README.md) — Phase 2 roadmap
- Article #4 (4-Stage Automation Ladder) — the policy framing
- Article #5 (Claude + MCP Replaced Our Pager) — the investigation flow that feeds the executor

## Why this is the natural capstone of Phase 2

Phase 1 (the original 6 layers) gave us a system that *understands* infrastructure. Phase 2 gives us a system that *acts* on it under safety constraints. The article is the moment that distinction clicks for the reader. It's also the article a Canadian SRE hiring manager will forward — "this engineer designed an automation system carefully enough to actually run it in production."
