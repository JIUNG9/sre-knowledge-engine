| Field | Value |
|---|---|
| Service | `auth-service` |
| Window | Mon 09:00-11:00 KST |
| Baseline P99 | 180 ms |
| Hotspot P99 | 1,240 ms |
| Event count over 180d | 45 (across ~26 Mondays) |
| Root cause (suspected) | Connection pool cold-start + 4x login throughput |
| Suggested action | Pre-warm pool at 08:45; pre-scale 3 -> 5 replicas at 08:30 |
