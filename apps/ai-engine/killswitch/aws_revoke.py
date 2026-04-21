"""AWS session revocation via inline IAM deny policy.

:func:`revoke_aws_session` attaches an inline policy named
``AWSRevokeOlderSessions`` to the target IAM role. The policy denies *every*
action for any session issued before "now" — the standard AWS break-glass
recipe.

This is **opt-in only**. It is guarded at two levels:

1. :class:`KillSwitchConfig.revoke_aws_on_panic` must be ``True``.
2. :class:`KillSwitchConfig.aws_role_arn` must be set.

The function is idempotent: calling it twice simply overwrites the previous
inline policy with a fresher timestamp (so any sessions issued between the
two calls are also revoked).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("aegis.killswitch.aws")

REVOKE_POLICY_NAME = "AWSRevokeOlderSessions"


def _build_policy_document(now_iso: str) -> dict[str, Any]:
    """Build the inline policy document that denies all older sessions."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AegisRevokeOlderSessions",
                "Effect": "Deny",
                "Action": ["*"],
                "Resource": ["*"],
                "Condition": {"DateLessThan": {"aws:TokenIssueTime": now_iso}},
            }
        ],
    }


def _extract_role_name(role_arn: str) -> str:
    """Extract the role name from an IAM role ARN.

    Accepts both plain role ARNs and role ARNs with a path, e.g.::

        arn:aws:iam::123456789012:role/aegis-agent
        arn:aws:iam::123456789012:role/service/aegis-agent
    """
    if not role_arn or ":role/" not in role_arn:
        raise ValueError(f"not a role ARN: {role_arn!r}")
    return role_arn.split(":role/", 1)[1]


def revoke_aws_session(
    role_arn: str,
    *,
    iam_client: Any | None = None,
) -> dict[str, Any]:
    """Revoke every session issued before *now* for ``role_arn``.

    Args:
        role_arn: Full IAM role ARN (``arn:aws:iam::<acct>:role/<name>``).
        iam_client: Optional pre-built boto3 IAM client. Tests inject a
            stub/mock here. If omitted, a new client is created via
            ``boto3.client("iam")``.

    Returns:
        A dict with ``role_arn``, ``role_name``, ``policy_name``,
        ``issued_before`` (the ISO timestamp recorded in the policy), and
        ``idempotent=True``.

    Raises:
        ValueError: If ``role_arn`` is not a valid role ARN.
        RuntimeError: If ``boto3`` is unavailable and no client was injected.
    """
    role_name = _extract_role_name(role_arn)

    if iam_client is None:
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - optional dep
            raise RuntimeError(
                "boto3 is required for AWS session revocation. "
                "Install with `pip install boto3`."
            ) from exc
        iam_client = boto3.client("iam")

    now_iso = datetime.now(timezone.utc).isoformat()
    policy_doc = _build_policy_document(now_iso)

    logger.critical(
        "Attaching %s inline deny policy to role %s (issued_before=%s)",
        REVOKE_POLICY_NAME,
        role_name,
        now_iso,
    )

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=REVOKE_POLICY_NAME,
        PolicyDocument=json.dumps(policy_doc),
    )

    return {
        "role_arn": role_arn,
        "role_name": role_name,
        "policy_name": REVOKE_POLICY_NAME,
        "issued_before": now_iso,
        "idempotent": True,
    }
