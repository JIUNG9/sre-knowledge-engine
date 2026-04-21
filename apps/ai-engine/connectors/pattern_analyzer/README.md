# Pattern Analyzer (Layer 2B)

Aegis's Pattern Analyzer turns a raw stream of incidents, alerts, or log lines
into a compact, structured picture of **when**, **what**, and **together with
what** incidents happen. It feeds Layer 3 (Claude Control Tower) enriched
context so the LLM reasons over patterns — not raw noise.

## What it detects

- **Day-of-week clustering** — e.g. "80% of incidents fire on Monday"
- **Hour-of-day skew** — peak minute-of-the-day across the whole window
- **(weekday, hour) hotspots** — the Monday-9am headline of Article #6
- **Week-over-week anomalies** — z-score vs. baseline mean/stdev
- **Bursts** — short spikes (default 60s windows, z >= 3)
- **Message clusters** — canonicalised templates (UUIDs, IPs, numbers, timestamps
  stripped) merged via MinHash + Jaccard on 3-shingles
- **Service correlation graph** — directed edges where
  `score(A->B) = P(B within window | A fired)`

## Worked example — the "Monday 9am" story

Feed 100 incidents, 80 of them on Monday around 09:00 UTC:

```python
from connectors.pattern_analyzer import PatternAnalyzer, build_analysis_report
from connectors.pattern_analyzer.tests.fixtures import monday_9am_events

events = monday_9am_events(total=100, monday_ratio=0.80, seed=42)
result = PatternAnalyzer().analyze(events)
report = build_analysis_report(result)
print(report["markdown"])
```

The markdown summary leads with:

> **Time concentration:** 80.0% of events on **Mon**, peak hour **09:00 UTC**
> (42.0% of all events).

The structured JSON (`report["json"]`) carries the full distributions,
hotspots, anomalies, bursts, clusters, and correlation edges — ready for
dashboards or regression tests.

## How to interpret a report

- `weekday_share >= 0.5`: strong temporal clustering — investigate a
  scheduled job, batch workload, or human-traffic skew.
- `week_anomalies` with `direction="spike"` and `|z| >= 2`: a week
  deviated enough from the trailing baseline to warrant a post-mortem.
- `bursts`: immediate operational signal — these are minute-scale
  pile-ups that usually map 1:1 to an incident.
- Correlation edges with `score >= 0.9`: these services are functionally
  coupled — a change freeze on A should also guard B.

## Design notes

Pure stdlib (no numpy), deterministic (fixed MinHash salts), memory-bounded
(streams with bucket counters; max-N caps on services and clusters). Tests
cover ~95% of branches; see `tests/`.
