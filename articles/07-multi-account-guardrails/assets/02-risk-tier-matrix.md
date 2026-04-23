| # | Action Type | Risk Tier | AWS-Specific Example | Automation Behavior |
|---|---|---|---|---|
| 1 | CloudWatch log query | NONE | `filter-log-events` on `/aws/eks/cluster-name` | Auto, no approval, no dry-run |
| 2 | CloudWatch metric read | NONE | `get-metric-statistics` on EKS pod metrics | Auto, no approval |
| 3 | Describe resources | NONE | `describe-db-instances`, `describe-clusters` | Auto, no approval |
| 4 | kubectl get / logs / describe | NONE | `kubectl get pods -n auth` | Auto, no approval |
| 5 | kubectl rollout restart (spoke) | LOW | `kubectl rollout restart deploy/auth-service` in spoke | Auto-approve with dry-run; post-verify |
| 6 | kubectl scale up (spoke) | LOW | `kubectl scale --replicas=7` (from 3) in spoke | Auto-approve with dry-run; post-verify |
| 7 | kubectl scale down (spoke) | MEDIUM | `kubectl scale --replicas=1` (from 5) in spoke | Slack approval required |
| 8 | kubectl delete pod (spoke) | MEDIUM | `kubectl delete pod auth-xxxx` | Slack approval required |
| 9 | kubectl rollout undo (spoke) | MEDIUM | Roll back to previous ReplicaSet | Slack approval required |
| 10 | Terraform apply (any account) | HIGH | `terraform apply` on any state file | Manual only, no AI execution ever |
| 11 | kubectl delete (non-pod) | HIGH | `kubectl delete deployment auth-service` | Manual only |
| 12 | RDS stop / modify | HIGH | `aws rds modify-db-instance` | Manual only |
| 13 | Any action in hub account | HIGH | Anything touching `111111111111` | Manual only, regardless of category |
| 14 | Any action in security account | BLOCKED | Anything touching `555555555555` | Never automated, ever |
| 15 | IAM policy modify | BLOCKED | `iam put-role-policy`, `iam attach-role-policy` | Hard-coded block — AI literally cannot attempt this |
| 16 | S3 public-access config change | BLOCKED | `s3api put-public-access-block` | Hard-coded block |
| 17 | S3 bucket policy modify | BLOCKED | `s3api put-bucket-policy` | Hard-coded block |
| 18 | Cross-account IAM role change | BLOCKED | `iam update-assume-role-policy` | Hard-coded block |
| 19 | Security Group rule modify | HIGH | `ec2 authorize-security-group-ingress` | Manual only |
| 20 | KMS key policy modify | BLOCKED | `kms put-key-policy` | Hard-coded block |
