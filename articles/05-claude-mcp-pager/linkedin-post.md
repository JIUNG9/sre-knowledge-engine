# LinkedIn — Article 5: Claude + MCP Replaced the Pager

Three variants. Pick one. Each targets 1,300 characters. No emojis. CTA to Medium + GitHub.

---

## Variant A — Technical

**Claude API plus MCP replaced my 3 AM pager workflow for fifteen dollars a month.**

The investigation loop:

1. SigNoz alert fires. Aegis ingests.
2. Wiki retrieves the relevant entity page (auth-service, its runbook, its recent incidents).
3. SigNoz connector pulls the last hour of logs, six hours of metrics, and any time-based patterns the analyzer has learned.
4. Claude Sonnet receives the bundle — wiki context plus live telemetry — and writes an investigation.
5. The agent proposes a specific remediation.
6. Guardrails gate the action by risk tier. Slack approval for medium-risk. Human-only for high-risk.
7. On approval, the action runs with a mandatory rollback plan. Post-validation verifies metrics improved. Audit trail captures everything.

Three modes: Eco (Haiku, ~0.001 USD per query), Standard (Sonnet, ~0.08 USD per investigation), Deep (Opus, ~0.25 USD for multi-service analysis). Budget cap auto-downgrades to Eco at the configured threshold.

It is not replacing the on-call engineer. It is making sure the on-call engineer opens their laptop to a complete investigation already in progress.

Full write-up: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#AI #SRE #MCP

---

## Variant B — Career

**I hated the 3 AM pager more than anything else in SRE work. So I built a replacement.**

Not a replacement for me — I still take the page. A replacement for the twenty minutes between "alert fires" and "I understand what is happening."

Aegis does the investigation before I reach my laptop. When my phone buzzes, the agent has already pulled logs, checked metrics, read the runbook, compared against recent incidents, and proposed a specific fix in Slack. I open the laptop to a complete briefing.

The cost is fifteen dollars a month. It runs on Claude Sonnet with prompt caching, SigNoz for observability, and an Obsidian vault for knowledge. Full stack is open source at github.com/JIUNG9/aegis.

I run SRE by day. Aegis is the evenings-and-weekends project that started because I was tired of being behind when the pager went off.

Relocating to Canada in 2027. Open to conversations with Canadian SRE teams.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#SRE #OnCall #PlatformEngineering

---

## Variant C — Hot take

**PagerDuty is a notification system. It does not investigate. It sends a push notification and hopes you remember how the system works.**

That is the actual bar AI has to clear. Not "replace the SRE." Just be better than the seven-year-old notification layer that everyone still pays for.

I built it. Alert fires. Aegis reads the wiki for the affected service. SigNoz connector pulls logs and metrics. Claude Sonnet writes an investigation. A specific fix lands in Slack before my laptop opens. Fifteen dollars a month, end to end.

This is the bar. The pager tells you something is wrong. Aegis tells you what is wrong, why, and what to do about it. The SRE still decides.

Full article: <medium-link-placeholder>

GitHub: github.com/JIUNG9/aegis

#AI #DevOps #SRE
