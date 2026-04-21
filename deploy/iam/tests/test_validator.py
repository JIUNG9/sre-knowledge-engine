"""
Unit tests for deploy/iam/validator.py.

Run with:
  python -m pytest deploy/iam/tests/ -v
  # or
  python deploy/iam/tests/test_validator.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Allow running from repo root or from the tests dir.
HERE = Path(__file__).resolve().parent
IAM_DIR = HERE.parent
sys.path.insert(0, str(IAM_DIR))

import validator  # noqa: E402


def _aws_good_identity_policy() -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowRead",
                "Effect": "Allow",
                "Action": ["ec2:Describe*", "logs:FilterLogEvents"],
                "Resource": "*",
            },
            {
                "Sid": "DenyMut",
                "Effect": "Deny",
                "Action": [
                    "*:Create*", "*:Delete*", "*:Put*", "*:Update*",
                    "*:Modify*",
                ],
                "Resource": "*",
            },
            {
                "Sid": "DenySvcs",
                "Effect": "Deny",
                "Action": [
                    "iam:*", "secretsmanager:*", "organizations:*", "ce:*",
                ],
                "Resource": "*",
            },
        ],
    }


def _aws_good_trust_policy() -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Assume",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "Bool": {"aws:MultiFactorAuthPresent": "true"},
                    "StringEquals": {"sts:ExternalId": "x" * 32},
                },
            }
        ],
    }


class TestAwsValidator(unittest.TestCase):

    def test_good_identity_policy_passes(self) -> None:
        rep = validator.Report()
        validator.validate_aws_policy(
            _aws_good_identity_policy(), "good.json", rep,
        )
        self.assertTrue(rep.ok(), f"unexpected errors: {rep.errors}")

    def test_good_trust_policy_passes(self) -> None:
        rep = validator.Report()
        validator.validate_aws_policy(
            _aws_good_trust_policy(), "trust.json", rep,
        )
        self.assertTrue(rep.ok(), f"unexpected errors: {rep.errors}")

    def test_allow_create_is_rejected(self) -> None:
        policy = _aws_good_identity_policy()
        policy["Statement"][0]["Action"].append("ec2:CreateVpc")
        rep = validator.Report()
        validator.validate_aws_policy(policy, "bad.json", rep)
        rules = {f.rule for f in rep.errors}
        self.assertIn("AWS-ALLOW-MUTATION", rules)

    def test_allow_put_object_rejected(self) -> None:
        policy = _aws_good_identity_policy()
        policy["Statement"][0]["Action"].append("s3:PutObject")
        rep = validator.Report()
        validator.validate_aws_policy(policy, "bad.json", rep)
        self.assertIn(
            "AWS-ALLOW-MUTATION", {f.rule for f in rep.errors},
        )

    def test_wildcard_allow_on_wildcard_rejected(self) -> None:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Bad",
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": "*",
                }
            ],
        }
        rep = validator.Report()
        validator.validate_aws_policy(policy, "bad.json", rep)
        rules = {f.rule for f in rep.errors}
        self.assertIn("AWS-WILDCARD-ALLOW", rules)

    def test_missing_iam_deny_flagged(self) -> None:
        policy = _aws_good_identity_policy()
        # Remove the DenySvcs statement.
        policy["Statement"] = [
            s for s in policy["Statement"] if s["Sid"] != "DenySvcs"
        ]
        rep = validator.Report()
        validator.validate_aws_policy(policy, "bad.json", rep)
        rules = {f.rule for f in rep.errors}
        self.assertIn("AWS-MISSING-DENY", rules)

    def test_missing_mutation_deny_flagged(self) -> None:
        policy = _aws_good_identity_policy()
        policy["Statement"] = [
            s for s in policy["Statement"] if s["Sid"] != "DenyMut"
        ]
        rep = validator.Report()
        validator.validate_aws_policy(policy, "bad.json", rep)
        rules = {f.rule for f in rep.errors}
        self.assertIn("AWS-MISSING-MUTATION-DENY", rules)

    def test_trust_policy_without_mfa_rejected(self) -> None:
        policy = _aws_good_trust_policy()
        policy["Statement"][0]["Condition"]["Bool"] = {
            "aws:SecureTransport": "true"
        }
        rep = validator.Report()
        validator.validate_aws_policy(policy, "bad.json", rep)
        rules = {f.rule for f in rep.errors}
        self.assertIn("AWS-TRUST-NO-MFA", rules)

    def test_describe_is_read_only(self) -> None:
        self.assertTrue(validator._action_is_read_only("ec2:DescribeInstances"))
        self.assertTrue(validator._action_is_read_only("logs:FilterLogEvents"))
        self.assertTrue(validator._action_is_read_only("sts:GetCallerIdentity"))

    def test_create_is_not_read_only(self) -> None:
        self.assertFalse(validator._action_is_read_only("ec2:CreateVpc"))
        self.assertFalse(validator._action_is_read_only("s3:PutObject"))
        self.assertFalse(validator._action_is_read_only("iam:AttachRolePolicy"))


class TestGcpValidator(unittest.TestCase):

    def test_read_only_perms_pass(self) -> None:
        role = {
            "includedPermissions": [
                "compute.instances.get",
                "compute.instances.list",
                "logging.logs.list",
                "storage.objects.get",
            ]
        }
        rep = validator.Report()
        validator.validate_gcp_role(role, "good.yaml", rep)
        self.assertTrue(rep.ok(), f"unexpected: {rep.errors}")

    def test_create_perm_rejected(self) -> None:
        role = {
            "includedPermissions": [
                "compute.instances.get",
                "compute.instances.create",
            ]
        }
        rep = validator.Report()
        validator.validate_gcp_role(role, "bad.yaml", rep)
        self.assertTrue(any(
            "compute.instances.create" in f.message for f in rep.errors
        ))

    def test_set_iam_policy_rejected(self) -> None:
        role = {
            "includedPermissions": [
                "resourcemanager.projects.setIamPolicy",
            ]
        }
        rep = validator.Report()
        validator.validate_gcp_role(role, "bad.yaml", rep)
        self.assertTrue(rep.errors)

    def test_act_as_rejected(self) -> None:
        role = {
            "includedPermissions": [
                "iam.serviceAccounts.actAs",
            ]
        }
        rep = validator.Report()
        validator.validate_gcp_role(role, "bad.yaml", rep)
        self.assertTrue(rep.errors)


class TestAzureValidator(unittest.TestCase):

    def test_read_actions_pass(self) -> None:
        role = {
            "Actions": [
                "Microsoft.Compute/virtualMachines/read",
                "Microsoft.Insights/metrics/read",
            ],
            "DataActions": [
                "Microsoft.Storage/storageAccounts/blobServices/"
                "containers/blobs/read",
            ],
        }
        rep = validator.Report()
        validator.validate_azure_role(role, "good.json", rep)
        self.assertTrue(rep.ok(), f"unexpected: {rep.errors}")

    def test_write_action_rejected(self) -> None:
        role = {
            "Actions": [
                "Microsoft.Compute/virtualMachines/write",
            ]
        }
        rep = validator.Report()
        validator.validate_azure_role(role, "bad.json", rep)
        self.assertIn(
            "AZURE-MUTATING-ACTION", {f.rule for f in rep.errors},
        )

    def test_delete_action_rejected(self) -> None:
        role = {
            "Actions": [
                "Microsoft.Compute/virtualMachines/delete",
            ]
        }
        rep = validator.Report()
        validator.validate_azure_role(role, "bad.json", rep)
        self.assertTrue(rep.errors)

    def test_elevate_access_rejected(self) -> None:
        role = {
            "Actions": [
                "Microsoft.Authorization/elevateAccess/action",
            ]
        }
        rep = validator.Report()
        validator.validate_azure_role(role, "bad.json", rep)
        self.assertTrue(rep.errors)

    def test_wildcard_rejected(self) -> None:
        role = {"Actions": ["*"]}
        rep = validator.Report()
        validator.validate_azure_role(role, "bad.json", rep)
        self.assertIn(
            "AZURE-WILDCARD-ACTION", {f.rule for f in rep.errors},
        )


class TestShippedPolicies(unittest.TestCase):
    """Ensure every policy we ship actually passes the validator."""

    def test_aws_readonly_policy(self) -> None:
        path = IAM_DIR / "aws" / "readonly-policy.json"
        rep = validator.Report()
        validator.validate_file(path, rep)
        self.assertTrue(
            rep.ok(), f"readonly-policy failures: {[str(e) for e in rep.errors]}",
        )

    def test_aws_trust_policy(self) -> None:
        path = IAM_DIR / "aws" / "trust-policy.json"
        rep = validator.Report()
        validator.validate_file(path, rep)
        self.assertTrue(
            rep.ok(), f"trust-policy failures: {[str(e) for e in rep.errors]}",
        )

    def test_aws_session_policy(self) -> None:
        path = IAM_DIR / "aws" / "session-policy-example.json"
        rep = validator.Report()
        validator.validate_file(path, rep)
        self.assertTrue(
            rep.ok(), f"session-policy failures: {[str(e) for e in rep.errors]}",
        )

    def test_gcp_role(self) -> None:
        path = IAM_DIR / "gcp" / "readonly-role.yaml"
        rep = validator.Report()
        validator.validate_file(path, rep)
        # PyYAML may be missing in some environments — skip with message.
        if not validator.YAML_OK:
            self.skipTest("PyYAML not installed")
        self.assertTrue(
            rep.ok(), f"gcp-role failures: {[str(e) for e in rep.errors]}",
        )

    def test_azure_role(self) -> None:
        path = IAM_DIR / "azure" / "readonly-role.json"
        rep = validator.Report()
        validator.validate_file(path, rep)
        self.assertTrue(
            rep.ok(), f"azure-role failures: {[str(e) for e in rep.errors]}",
        )

    def test_policies_are_valid_json(self) -> None:
        for rel in (
            "aws/readonly-policy.json",
            "aws/trust-policy.json",
            "aws/session-policy-example.json",
            "azure/readonly-role.json",
        ):
            with (IAM_DIR / rel).open() as f:
                try:
                    json.load(f)
                except Exception as exc:
                    self.fail(f"{rel} is not valid JSON: {exc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
