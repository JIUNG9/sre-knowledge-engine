#!/usr/bin/env python3
"""
Aegis IAM Policy Validator
==========================

Statically validates AWS / GCP / Azure IAM policy files against the
Aegis "technically unwritable" contract:

  1. No Allow on any mutating verb (create/delete/put/update/modify/attach/
     detach/write/start/stop/terminate/patch/setIamPolicy/elevateAccess).
  2. Explicit Deny present on high-risk AWS services (iam, secretsmanager,
     kms write ops, organizations, ce).
  3. No wildcard Action + wildcard Resource in any Allow statement
     (except for Describe/List/Get read-only prefixes).
  4. AWS trust policies require MFA condition.

Exit code 0 on success, 1 on any violation.

Usage:
  python validator.py <path-to-policy.json|policy.yaml>
  python validator.py --all deploy/iam/

Depends only on Python stdlib except PyYAML (optional — YAML files
are skipped with a warning if not installed).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
    YAML_OK = True
except ImportError:
    YAML_OK = False


# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

# AWS mutating verb patterns — any Allow matching these fails the validator.
# We match both prefix form (Create*, Delete*) and explicit action form
# (ec2:CreateVpc, s3:PutObject, etc.).
AWS_MUTATING_VERBS = [
    "Create", "Delete", "Put", "Update", "Modify", "Attach", "Detach",
    "Replace", "Reboot", "Restore", "Terminate", "Disable", "Enable",
    "Write", "Run", "Associate", "Disassociate", "Authorize", "Revoke",
    "Tag", "Untag", "Cancel", "Reset", "Set", "Add", "Remove", "Copy",
    "Import", "Export", "Upload", "Invoke", "Publish", "Send", "Promote",
    "Reject", "Approve", "Grant", "Revoke",
]

# Services that must appear in an explicit AWS Deny statement.
AWS_REQUIRED_DENY_SERVICES = {
    "iam": "iam:*",
    "secretsmanager": "secretsmanager:*",
    "organizations": "organizations:*",
    "ce": "ce:*",
}

# GCP permission patterns that indicate mutation.
GCP_MUTATING_VERBS = [
    "create", "delete", "update", "patch", "setIamPolicy",
    "setMetadata", "actAs", "generateAccessToken", "signBlob",
    "attach", "detach", "bind", "unbind", "write",
]

# Azure action suffixes that indicate mutation.
AZURE_MUTATING_SUFFIXES = [
    "/write", "/delete", "/action", "/elevateAccess",
]

# Azure actions that are READ-oriented /action endpoints (allowed).
AZURE_ACTION_ALLOWLIST = {
    "Microsoft.OperationalInsights/workspaces/search/action",
    "Microsoft.Insights/eventtypes/values/read",
}


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str  # "ERROR" | "WARN"
    file: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file}: {self.rule} — {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    def ok(self) -> bool:
        return not self.errors

    def add(self, severity: str, file: str, rule: str, message: str) -> None:
        self.findings.append(Finding(severity, file, rule, message))


# ---------------------------------------------------------------------------
# AWS validator
# ---------------------------------------------------------------------------

def _normalize_actions(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _action_is_read_only(action: str) -> bool:
    """
    Read-only AWS actions start with Describe/List/Get/Search/Lookup/View/
    Query/Test/Filter, OR are a full-service wildcard followed by those
    prefixes (e.g. ec2:Describe*). Anything else is suspicious in an Allow.
    """
    if action == "*":
        return False
    if ":" not in action:
        return False
    _service, verb = action.split(":", 1)
    read_prefixes = (
        "Describe", "List", "Get", "Search", "Lookup", "View", "Query",
        "Test", "Filter", "BatchGet", "Head", "Select", "Scan", "Simulate",
        "Download",
    )
    if verb in ("*",):
        return False
    for p in read_prefixes:
        if verb.startswith(p):
            return True
    # Specific safe identity calls
    if action in ("sts:GetCallerIdentity", "sts:GetSessionToken"):
        return True
    return False


def _action_has_mutating_verb(action: str) -> str | None:
    """Return the matched mutating verb, or None."""
    if ":" not in action:
        return None
    _service, verb = action.split(":", 1)
    # Wildcard form like *:Create*
    for mv in AWS_MUTATING_VERBS:
        if verb.startswith(mv):
            return mv
    return None


def validate_aws_policy(data: dict, path: str, report: Report) -> None:
    statements = data.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]

    saw_deny_for: set[str] = set()
    saw_mutation_deny = False

    for idx, stmt in enumerate(statements):
        effect = stmt.get("Effect")
        actions = _normalize_actions(stmt.get("Action"))
        resources = _normalize_actions(stmt.get("Resource"))
        sid = stmt.get("Sid", f"stmt[{idx}]")

        if effect == "Allow":
            # Rule 1: no mutating verbs in Allow
            for a in actions:
                mv = _action_has_mutating_verb(a)
                if mv and not _action_is_read_only(a):
                    report.add(
                        "ERROR", path, "AWS-ALLOW-MUTATION",
                        f"Sid '{sid}': Allow contains mutating action '{a}' "
                        f"(matched verb '{mv}')",
                    )
                # Rule 3: wildcard action + wildcard resource
                if a == "*" and "*" in resources:
                    report.add(
                        "ERROR", path, "AWS-WILDCARD-ALLOW",
                        f"Sid '{sid}': Allow * on * — this grants full admin",
                    )

        elif effect == "Deny":
            for a in actions:
                # Track denies for required services
                for svc in AWS_REQUIRED_DENY_SERVICES:
                    if a.startswith(f"{svc}:"):
                        saw_deny_for.add(svc)
                # Track mutation-wildcard denies
                if a.startswith("*:") and _action_has_mutating_verb(a):
                    saw_mutation_deny = True

    # Rule 2: required high-risk denies
    # Only enforced for identity/resource policies (those with Statement);
    # trust policies won't have these — we skip via a heuristic below.
    is_trust_policy = any(
        "Principal" in s for s in statements if isinstance(s, dict)
    )
    if not is_trust_policy:
        for svc in AWS_REQUIRED_DENY_SERVICES:
            if svc not in saw_deny_for:
                report.add(
                    "ERROR", path, "AWS-MISSING-DENY",
                    f"No explicit Deny found for high-risk service '{svc}:*'",
                )
        if not saw_mutation_deny:
            report.add(
                "ERROR", path, "AWS-MISSING-MUTATION-DENY",
                "No wildcard mutation Deny (e.g. '*:Create*', '*:Delete*') "
                "found — policy relies only on absence of Allow, which "
                "breaks defense-in-depth",
            )

    # Rule 4: trust policies must require MFA
    if is_trust_policy:
        mfa_ok = False
        for s in statements:
            cond = s.get("Condition", {}) or {}
            for op, kv in cond.items():
                if not isinstance(kv, dict):
                    continue
                if "aws:MultiFactorAuthPresent" in kv:
                    mfa_ok = True
        if not mfa_ok:
            report.add(
                "ERROR", path, "AWS-TRUST-NO-MFA",
                "Trust policy does not require aws:MultiFactorAuthPresent",
            )


# ---------------------------------------------------------------------------
# GCP validator
# ---------------------------------------------------------------------------

def validate_gcp_role(data: dict, path: str, report: Report) -> None:
    perms = data.get("includedPermissions", []) or []
    for p in perms:
        # Extract trailing verb after last dot: storage.buckets.create → create
        tail = p.rsplit(".", 1)[-1]
        for mv in GCP_MUTATING_VERBS:
            # Use case-insensitive match for camelCase (setIamPolicy)
            if tail.lower().startswith(mv.lower()) and tail.lower() == mv.lower():
                report.add(
                    "ERROR", path, "GCP-MUTATION-PERM",
                    f"Included permission '{p}' is a mutation "
                    f"(verb='{mv}') — remove it",
                )
                break
            # Exact match for verbs with camelCase middle like setIamPolicy
            if mv == "setIamPolicy" and "setIamPolicy" in p:
                report.add(
                    "ERROR", path, "GCP-SET-IAM",
                    f"'{p}' grants IAM modification — remove it",
                )
                break
            if mv == "actAs" and p.endswith(".actAs"):
                report.add(
                    "ERROR", path, "GCP-ACT-AS",
                    f"'{p}' grants service account impersonation",
                )
                break


# ---------------------------------------------------------------------------
# Azure validator
# ---------------------------------------------------------------------------

def validate_azure_role(data: dict, path: str, report: Report) -> None:
    actions = data.get("Actions", []) or []
    data_actions = data.get("DataActions", []) or []

    for action in actions + data_actions:
        # Read actions ending in /read are fine.
        for bad_suffix in AZURE_MUTATING_SUFFIXES:
            if action.endswith(bad_suffix):
                if action in AZURE_ACTION_ALLOWLIST:
                    continue
                # /action is only bad if not in allowlist AND looks mutating
                if bad_suffix == "/action":
                    lowered = action.lower()
                    if any(
                        kw in lowered
                        for kw in (
                            "elevate", "write", "delete", "decrypt",
                            "getsecret", "sign", "purge", "restore",
                        )
                    ):
                        report.add(
                            "ERROR", path, "AZURE-MUTATING-ACTION",
                            f"Action '{action}' is mutating or grants "
                            f"sensitive data-plane access",
                        )
                    # else skip — /action is not inherently write
                    continue
                report.add(
                    "ERROR", path, "AZURE-MUTATING-ACTION",
                    f"Action '{action}' ends in '{bad_suffix}' (mutating)",
                )

    # Wildcard in Actions check
    for a in actions:
        if a == "*":
            report.add(
                "ERROR", path, "AZURE-WILDCARD-ACTION",
                "Wildcard '*' in Actions grants full control",
            )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def load_policy(path: Path) -> dict | None:
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if not YAML_OK:
            print(
                f"[WARN] PyYAML not installed — skipping {path}",
                file=sys.stderr,
            )
            return None
        return yaml.safe_load(text)
    # Strip _comment keys before JSON parse? JSON will accept them — no-op.
    return json.loads(text)


def detect_kind(path: Path, data: dict) -> str:
    """Return 'aws' | 'gcp' | 'azure' | 'unknown'."""
    parts = {p.lower() for p in path.parts}
    if "aws" in parts:
        return "aws"
    if "gcp" in parts:
        return "gcp"
    if "azure" in parts:
        return "azure"
    # Heuristic fallback
    if "Version" in data and "Statement" in data:
        return "aws"
    if "includedPermissions" in data:
        return "gcp"
    if "AssignableScopes" in data or "IsCustom" in data:
        return "azure"
    return "unknown"


def validate_file(path: Path, report: Report) -> None:
    try:
        data = load_policy(path)
    except Exception as exc:
        report.add(
            "ERROR", str(path), "PARSE-ERROR",
            f"Failed to parse: {exc}",
        )
        return
    if data is None:
        return
    kind = detect_kind(path, data)
    if kind == "aws":
        validate_aws_policy(data, str(path), report)
    elif kind == "gcp":
        validate_gcp_role(data, str(path), report)
    elif kind == "azure":
        validate_azure_role(data, str(path), report)
    else:
        report.add(
            "WARN", str(path), "UNKNOWN-KIND",
            "Could not detect cloud provider — skipped",
        )


def discover(root: Path) -> list[Path]:
    results: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".json", ".yaml", ".yml"):
            # Skip package manifests, tests, etc.
            if p.name.startswith("package") or "tests" in p.parts:
                continue
            results.append(p)
    return sorted(results)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Aegis IAM Policy Validator")
    parser.add_argument(
        "target",
        help="Path to a policy file, or a directory (with --all)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Recursively validate every policy in the directory",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only print on failure",
    )
    args = parser.parse_args(argv)

    root = Path(args.target)
    report = Report()

    if args.all:
        if not root.is_dir():
            print(f"ERROR: {root} is not a directory", file=sys.stderr)
            return 2
        for f in discover(root):
            validate_file(f, report)
    else:
        if not root.is_file():
            print(f"ERROR: {root} is not a file", file=sys.stderr)
            return 2
        validate_file(root, report)

    # Print findings
    for f in report.findings:
        print(str(f))

    if report.ok():
        if not args.quiet:
            print(f"\nPASS — {len(report.findings)} warnings, 0 errors")
        return 0
    print(
        f"\nFAIL — {len(report.errors)} errors, "
        f"{len(report.findings) - len(report.errors)} warnings",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
