| Action | Risk | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|---|---|---|---|---|---|
| `query_logs`, `query_metrics`, `describe_pod` | Read-only | auto | auto | auto | auto |
| Update staging env var | Low | observe | recommend | auto | auto |
| `kubectl scale --replicas=N` (up) | Low | observe | recommend | auto | auto |
| Cache flush (single service) | Low | observe | recommend | auto | auto |
| `kubectl rollout restart deployment/X` | Medium | observe | recommend | recommend | auto |
| `kubectl rollout undo` | Medium | observe | recommend | recommend | auto |
| Scale-down prod deployment | Medium | observe | recommend | recommend | auto |
| Update prod config (non-secret) | Medium | observe | recommend | recommend | auto |
| `terraform apply` (any) | High | observe | recommend | recommend | approval |
| Multi-service rollback | High | observe | recommend | recommend | approval |
| `kubectl delete` anything | High | observe | recommend | recommend | approval |
| IAM role / policy change | Blocked | never | never | never | never |
| Data mutation / deletion | Blocked | never | never | never | never |
