| Field | Value |
|---|---|
| Service | `analytics-worker` -> `postgres-primary` |
| Window | Mon 02:00-04:00 KST |
| Baseline write IOPS | 2,100 |
| Hotspot write IOPS | 14,800 |
| Event count over 180d | 22 (all Mondays; no misses) |
| Root cause | Weekly reconcile job rewrites 3 materialized views |
| Suggested action | Stagger view rebuilds; move 1 of 3 to Sunday 23:00 |
