| Step | Before (manual) | After (with Control Tower) |
|---|---|---|
| Alert fires → on-call acknowledges | 30 sec | 30 sec |
| Find the right runbook | 3–8 min | 0 sec (wiki context in Slack) |
| Pull SigNoz logs + metrics | 4–10 min | 0 sec (pre-fetched in context) |
| Correlate with recent incidents | 5–15 min | 0 sec (pattern analyzer did it) |
| Form a hypothesis | 2–5 min | 0 sec (in Slack card) |
| Decide on an action | 1–3 min | 15–45 sec (read card, click) |
| Execute | 1–2 min | 30–90 sec (auto or Slack-approved) |
| Verify fix worked | 3–5 min | Auto (post-validator, 60 sec) |
| **Total p50** | **~20 min** | **~2 min** |
| **Total p95 (harder incidents)** | **~45 min** | **~5 min** |
