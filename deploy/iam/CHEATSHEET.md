# Aegis IAM Cheatsheet

Quick reference for what each shipped policy allows and denies. Keep this open
while reviewing agent behavior or triaging an access-denied error.

## AWS — `aws/readonly-policy.json`

### Allow
| Service | Actions |
|---|---|
| EC2 | `Describe*`, `Get*`, `List*`, `Search*` |
| CloudWatch Logs | `Describe*`, `Get*`, `List*`, `FilterLogEvents`, `StartQuery`/`StopQuery`/`TestMetricFilter` |
| CloudWatch | `Describe*`, `Get*`, `List*` |
| RDS | `Describe*`, `List*`, `DownloadDBLogFilePortion` |
| EKS | `Describe*`, `List*` |
| S3 | `GetObject`, `GetObjectVersion`, `GetObjectTagging`, `ListBucket`, `ListAllMyBuckets`, `GetBucketLocation`/`Tagging`/`Logging` |
| STS | `GetCallerIdentity` |

### Deny (wildcard — overrides any future Allow)
| Pattern | Meaning |
|---|---|
| `*:Create*`, `*:Delete*`, `*:Put*`, `*:Update*`, `*:Modify*` | No resource creation, deletion, or mutation anywhere |
| `*:Attach*`, `*:Detach*`, `*:Associate*`, `*:Disassociate*` | No policy or resource re-linking |
| `*:Start*`, `*:Stop*`, `*:Reboot*`, `*:Terminate*` | No lifecycle changes |
| `*:Tag*`, `*:Untag*` | No tag mutation (prevents cost-allocation tampering) |
| `iam:*` | No IAM reads or writes (prevents privilege escalation paths) |
| `secretsmanager:*` | No secret access at all |
| `kms:Decrypt`, `kms:Encrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*` | No crypto ops |
| `organizations:*`, `sso:*`, `identitystore:*` | No org-level access |
| `ce:*`, `billing:*`, `account:*` | No Cost Explorer (charges per call) |
| `s3:PutObject*`, `s3:DeleteObject*`, `s3:PutBucket*`, `s3:DeleteBucket*` | No S3 writes |

## AWS — `aws/trust-policy.json`
Conditions required to assume the role:
- `aws:MultiFactorAuthPresent = true`
- `aws:MultiFactorAuthAge < 3600` (1h freshness)
- `aws:SecureTransport = true`
- `sts:ExternalId` matches shared secret (confused-deputy defense)

## AWS — `aws/session-policy-example.json`
Tightens the session further:
- Region-scoped to `us-east-1` + `us-west-2`
- Even smaller Allow surface (only `Describe*`/`Get*`/`List*`)
- Duplicate mutation denies for defense-in-depth

## GCP — `gcp/readonly-role.yaml`
Custom role title: **Aegis Read-Only Agent**
- Allows: Compute, GKE, Cloud Logging, Cloud Monitoring, Cloud Storage (object-read), Cloud SQL metadata, STS identity
- Explicitly excludes: `setIamPolicy`, `actAs`, `secretmanager.versions.access`, any `.create`/`.update`/`.delete`/`.patch`

## Azure — `azure/readonly-role.json`
Custom role name: **Aegis Read-Only Agent**
- Allows: `*/read` on Compute, Network, AKS, Insights, Log Analytics, Storage, SQL
- DataActions: only blob read
- NotDataActions (explicit block): Key Vault secret/key ops, blob write/delete
- NotActions: authorization write/delete, elevateAccess

## Validator — `validator.py`
```bash
python3 deploy/iam/validator.py --all deploy/iam/
```
Rules enforced:
- `AWS-ALLOW-MUTATION` — flags any Allow containing a mutating verb
- `AWS-WILDCARD-ALLOW` — flags `Allow *` on `Resource *`
- `AWS-MISSING-DENY` — required Deny for `iam`, `secretsmanager`, `organizations`, `ce` missing
- `AWS-MISSING-MUTATION-DENY` — no wildcard mutation Deny present
- `AWS-TRUST-NO-MFA` — trust policy without MFA condition
- `GCP-MUTATION-PERM`, `GCP-SET-IAM`, `GCP-ACT-AS` — mutation/impersonation perms in custom role
- `AZURE-MUTATING-ACTION`, `AZURE-WILDCARD-ACTION` — write/delete/elevate or wildcard

## Apply (DRY-RUN ONLY)
```bash
bash deploy/iam/apply.sh          # prints commands, never calls AWS
bash deploy/iam/apply.sh --print-only
```
