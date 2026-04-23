| File | Role |
|---|---|
| [`apps/ai-engine/guardrails/engine.py`](https://github.com/JIUNG9/aegis) | Main guardrails orchestrator |
| [`apps/ai-engine/guardrails/risk_assessor.py`](https://github.com/JIUNG9/aegis) | Classifies actions into NONE/LOW/MEDIUM/HIGH/BLOCKED |
| [`apps/ai-engine/guardrails/observation_mode.py`](https://github.com/JIUNG9/aegis) | Trust-building ladder (Observe / Recommend / Low-Auto / Full-Auto) |
| [`apps/ai-engine/guardrails/approval_gate.py`](https://github.com/JIUNG9/aegis) | Slack approval integration for MEDIUM tier |
| [`apps/ai-engine/guardrails/pre_validator.py`](https://github.com/JIUNG9/aegis) | Dry-run, IAM simulator, OPA checks |
| [`apps/ai-engine/guardrails/post_validator.py`](https://github.com/JIUNG9/aegis) | Metric watch + auto-rollback trigger |
| [`apps/ai-engine/guardrails/rollback_manager.py`](https://github.com/JIUNG9/aegis) | Enforces rollback plan; arms rollback window |
| [`apps/ai-engine/guardrails/audit_logger.py`](https://github.com/JIUNG9/aegis) | SOC2-compliant decision record writer |
| [`apps/ai-engine/guardrails/policies/`](https://github.com/JIUNG9/aegis) | OPA/Rego policies (versioned) |
