package mock

import (
	"time"

	"github.com/junegu/aegis/api/models"
)

// now anchors all mock timestamps relative to a consistent point.
var now = time.Date(2026, 4, 10, 12, 0, 0, 0, time.UTC)

func ptr(t time.Time) *time.Time { return &t }

// Incidents returns 10 realistic mock incidents with full timelines.
func Incidents() []models.Incident {
	return []models.Incident{
		{
			ID:          "INC-001",
			Title:       "Payment service high error rate",
			Description: "Payment service returning 500 errors at 15% rate, affecting checkout flow. Downstream Stripe webhook handler timing out under load.",
			Severity:    models.SeverityCritical,
			Status:      models.IncidentStatusInvestigating,
			Service:     "payment-service",
			Assignee:    "oncall-sre",
			Timeline: []models.TimelineEvent{
				{ID: "TL-001", IncidentID: "INC-001", Type: models.TimelineEventAlertFired, Actor: "signoz", Message: "Alert fired: payment_error_rate > 10% for 5m", Metadata: map[string]string{"alert_name": "PaymentHighErrorRate", "threshold": "10%", "current": "15.3%"}, Timestamp: now.Add(-3*time.Hour - 30*time.Minute)},
				{ID: "TL-002", IncidentID: "INC-001", Type: models.TimelineEventAcknowledged, Actor: "oncall-sre", Message: "Acknowledged by on-call SRE", Timestamp: now.Add(-3*time.Hour - 25*time.Minute)},
				{ID: "TL-003", IncidentID: "INC-001", Type: models.TimelineEventStatusChange, Actor: "oncall-sre", Message: "Status changed to investigating", Metadata: map[string]string{"from": "open", "to": "investigating"}, Timestamp: now.Add(-3*time.Hour - 24*time.Minute)},
				{ID: "TL-004", IncidentID: "INC-001", Type: models.TimelineEventNoteAdded, Actor: "oncall-sre", Message: "Stripe webhook handler shows connection pool exhaustion. Scaling up replicas while investigating root cause.", Timestamp: now.Add(-3 * time.Hour)},
				{ID: "TL-005", IncidentID: "INC-001", Type: models.TimelineEventEscalated, Actor: "oncall-sre", Message: "Escalated to payment team lead — potential data consistency issue", Timestamp: now.Add(-2*time.Hour - 30*time.Minute)},
			},
			RelatedAlerts: []string{"ALT-001", "ALT-002"},
			CreatedAt:     now.Add(-3*time.Hour - 30*time.Minute),
			UpdatedAt:     now.Add(-2*time.Hour - 30*time.Minute),
			Duration:      12600, // 3.5 hours ongoing
		},
		{
			ID:          "INC-002",
			Title:       "Elevated latency on user-service /api/v1/profile",
			Description: "P99 latency increased from 200ms to 1.2s on profile endpoint. Correlated with new deployment v2.14.0 containing N+1 query regression.",
			Severity:    models.SeverityHigh,
			Status:      models.IncidentStatusIdentified,
			Service:     "user-service",
			Assignee:    "backend-team",
			Timeline: []models.TimelineEvent{
				{ID: "TL-006", IncidentID: "INC-002", Type: models.TimelineEventAlertFired, Actor: "prometheus", Message: "Alert fired: user_service_latency_p99 > 1s for 10m", Metadata: map[string]string{"alert_name": "HighLatency", "endpoint": "/api/v1/profile"}, Timestamp: now.Add(-2 * time.Hour)},
				{ID: "TL-007", IncidentID: "INC-002", Type: models.TimelineEventAcknowledged, Actor: "backend-team", Message: "Acknowledged by backend team", Timestamp: now.Add(-1*time.Hour - 50*time.Minute)},
				{ID: "TL-008", IncidentID: "INC-002", Type: models.TimelineEventStatusChange, Actor: "backend-team", Message: "Status changed to identified — N+1 query found in profile endpoint", Metadata: map[string]string{"from": "investigating", "to": "identified"}, Timestamp: now.Add(-1*time.Hour - 20*time.Minute)},
				{ID: "TL-009", IncidentID: "INC-002", Type: models.TimelineEventNoteAdded, Actor: "backend-team", Message: "Root cause: v2.14.0 introduced eager loading of user preferences without batching. Fix PR #1847 submitted.", Timestamp: now.Add(-1 * time.Hour)},
			},
			RelatedAlerts: []string{"ALT-003"},
			RootCause:     "N+1 query regression in v2.14.0 profile endpoint eager loading user preferences without batching.",
			CreatedAt:     now.Add(-2 * time.Hour),
			UpdatedAt:     now.Add(-1 * time.Hour),
			Duration:      7200, // 2 hours ongoing
		},
		{
			ID:          "INC-003",
			Title:       "Kubernetes node NotReady in prod-us-east-1",
			Description: "Node i-0abc123 entered NotReady state due to kubelet OOM. Workloads rescheduled automatically by cluster autoscaler.",
			Severity:    models.SeverityMedium,
			Status:      models.IncidentStatusResolved,
			Service:     "infrastructure",
			Assignee:    "platform-team",
			Timeline: []models.TimelineEvent{
				{ID: "TL-010", IncidentID: "INC-003", Type: models.TimelineEventAlertFired, Actor: "prometheus", Message: "Alert fired: KubeNodeNotReady for node i-0abc123", Timestamp: now.Add(-22 * time.Hour)},
				{ID: "TL-011", IncidentID: "INC-003", Type: models.TimelineEventAcknowledged, Actor: "platform-team", Message: "Acknowledged by platform team", Timestamp: now.Add(-21*time.Hour - 45*time.Minute)},
				{ID: "TL-012", IncidentID: "INC-003", Type: models.TimelineEventStatusChange, Actor: "platform-team", Message: "Status changed to investigating", Metadata: map[string]string{"from": "open", "to": "investigating"}, Timestamp: now.Add(-21*time.Hour - 40*time.Minute)},
				{ID: "TL-013", IncidentID: "INC-003", Type: models.TimelineEventNoteAdded, Actor: "platform-team", Message: "Kubelet OOM caused by logging sidecar memory leak. Updated sidecar to v2.3.1.", Timestamp: now.Add(-20*time.Hour - 15*time.Minute)},
				{ID: "TL-014", IncidentID: "INC-003", Type: models.TimelineEventResolved, Actor: "platform-team", Message: "Node recovered after sidecar update. All pods healthy.", Timestamp: now.Add(-19*time.Hour - 15*time.Minute)},
			},
			RelatedAlerts: []string{"ALT-004", "ALT-005"},
			RootCause:     "Memory leak in logging sidecar container consuming 4Gi. Fixed by updating sidecar image to v2.3.1.",
			Remediation:   "Updated logging sidecar to v2.3.1 across all nodes. Added memory limits to sidecar DaemonSet.",
			CreatedAt:     now.Add(-22 * time.Hour),
			UpdatedAt:     now.Add(-19*time.Hour - 15*time.Minute),
			ResolvedAt:    ptr(now.Add(-19*time.Hour - 15*time.Minute)),
			Duration:      9900, // ~2h 45m
		},
		{
			ID:          "INC-004",
			Title:       "Certificate expiry warning for api.aegis.dev",
			Description: "TLS certificate for api.aegis.dev expires in 7 days. cert-manager renewal job failed due to DNS challenge timeout.",
			Severity:    models.SeverityLow,
			Status:      models.IncidentStatusMonitoring,
			Service:     "gateway",
			Assignee:    "infra-oncall",
			Timeline: []models.TimelineEvent{
				{ID: "TL-015", IncidentID: "INC-004", Type: models.TimelineEventAlertFired, Actor: "prometheus", Message: "Alert fired: CertExpiryWarning — api.aegis.dev expires in 7 days", Timestamp: now.Add(-6 * time.Hour)},
				{ID: "TL-016", IncidentID: "INC-004", Type: models.TimelineEventAcknowledged, Actor: "infra-oncall", Message: "Acknowledged. Checking cert-manager logs.", Timestamp: now.Add(-5*time.Hour - 30*time.Minute)},
				{ID: "TL-017", IncidentID: "INC-004", Type: models.TimelineEventNoteAdded, Actor: "infra-oncall", Message: "DNS challenge failing due to Route53 IAM role permissions change. Manual renewal triggered, monitoring.", Timestamp: now.Add(-5 * time.Hour)},
				{ID: "TL-018", IncidentID: "INC-004", Type: models.TimelineEventStatusChange, Actor: "infra-oncall", Message: "Status changed to monitoring — manual cert issued, fixing IAM role", Metadata: map[string]string{"from": "investigating", "to": "monitoring"}, Timestamp: now.Add(-4*time.Hour - 30*time.Minute)},
			},
			RelatedAlerts: []string{"ALT-006"},
			CreatedAt:     now.Add(-6 * time.Hour),
			UpdatedAt:     now.Add(-4*time.Hour - 30*time.Minute),
			Duration:      21600, // 6 hours ongoing
		},
		{
			ID:          "INC-005",
			Title:       "Database connection pool exhaustion on order-service",
			Description: "order-service Aurora PostgreSQL connection pool saturated at 100%. New requests queuing, causing cascading timeouts in checkout flow.",
			Severity:    models.SeverityCritical,
			Status:      models.IncidentStatusResolved,
			Service:     "order-service",
			Assignee:    "dba-oncall",
			Timeline: []models.TimelineEvent{
				{ID: "TL-019", IncidentID: "INC-005", Type: models.TimelineEventAlertFired, Actor: "cloudwatch", Message: "Alert fired: RDS connection count > 95% of max_connections", Metadata: map[string]string{"db_instance": "prod-orders-primary", "connections": "195/200"}, Timestamp: now.Add(-26 * time.Hour)},
				{ID: "TL-020", IncidentID: "INC-005", Type: models.TimelineEventAcknowledged, Actor: "dba-oncall", Message: "Acknowledged by DBA on-call", Timestamp: now.Add(-25*time.Hour - 50*time.Minute)},
				{ID: "TL-021", IncidentID: "INC-005", Type: models.TimelineEventStatusChange, Actor: "dba-oncall", Message: "Status changed to investigating", Metadata: map[string]string{"from": "open", "to": "investigating"}, Timestamp: now.Add(-25*time.Hour - 48*time.Minute)},
				{ID: "TL-022", IncidentID: "INC-005", Type: models.TimelineEventNoteAdded, Actor: "dba-oncall", Message: "Long-running queries from batch job holding connections. Killed 40 idle sessions. Increased max_connections to 300.", Timestamp: now.Add(-25 * time.Hour)},
				{ID: "TL-023", IncidentID: "INC-005", Type: models.TimelineEventStatusChange, Actor: "dba-oncall", Message: "Status changed to identified — batch job missing connection timeout", Metadata: map[string]string{"from": "investigating", "to": "identified"}, Timestamp: now.Add(-24*time.Hour - 30*time.Minute)},
				{ID: "TL-024", IncidentID: "INC-005", Type: models.TimelineEventResolved, Actor: "dba-oncall", Message: "Batch job patched with connection timeout. Pool usage stable at 45%.", Timestamp: now.Add(-24 * time.Hour)},
			},
			RelatedAlerts: []string{"ALT-007", "ALT-008"},
			RootCause:     "Batch reconciliation job missing connection timeout, leaking connections during long-running queries.",
			Remediation:   "Added 30s connection timeout to batch job. Increased max_connections to 300. Added PgBouncer connection pooler.",
			CreatedAt:     now.Add(-26 * time.Hour),
			UpdatedAt:     now.Add(-24 * time.Hour),
			ResolvedAt:    ptr(now.Add(-24 * time.Hour)),
			Duration:      7200, // 2 hours
		},
		{
			ID:          "INC-006",
			Title:       "Redis cluster failover in prod-ap-northeast-1",
			Description: "ElastiCache Redis primary node failed health checks. Automatic failover promoted replica. Brief (12s) connection drops observed across session-dependent services.",
			Severity:    models.SeverityHigh,
			Status:      models.IncidentStatusResolved,
			Service:     "cache-layer",
			Assignee:    "platform-team",
			Timeline: []models.TimelineEvent{
				{ID: "TL-025", IncidentID: "INC-006", Type: models.TimelineEventAlertFired, Actor: "cloudwatch", Message: "Alert fired: ElastiCache primary node health check failure", Timestamp: now.Add(-48 * time.Hour)},
				{ID: "TL-026", IncidentID: "INC-006", Type: models.TimelineEventAcknowledged, Actor: "platform-team", Message: "Auto-failover triggered. Acknowledged.", Timestamp: now.Add(-47*time.Hour - 55*time.Minute)},
				{ID: "TL-027", IncidentID: "INC-006", Type: models.TimelineEventNoteAdded, Actor: "platform-team", Message: "Failover completed in 12s. Session service reconnected. Verifying data consistency.", Timestamp: now.Add(-47*time.Hour - 40*time.Minute)},
				{ID: "TL-028", IncidentID: "INC-006", Type: models.TimelineEventResolved, Actor: "platform-team", Message: "All services reconnected. No data loss detected. Root cause: network partition on primary AZ.", Timestamp: now.Add(-47 * time.Hour)},
			},
			RelatedAlerts: []string{"ALT-009"},
			RootCause:     "Transient network partition in ap-northeast-1a AZ caused primary node to fail health checks.",
			Remediation:   "No action needed — automatic failover worked as designed. Added cross-AZ replication monitoring.",
			CreatedAt:     now.Add(-48 * time.Hour),
			UpdatedAt:     now.Add(-47 * time.Hour),
			ResolvedAt:    ptr(now.Add(-47 * time.Hour)),
			Duration:      3600, // 1 hour
		},
		{
			ID:          "INC-007",
			Title:       "CI/CD pipeline failures across all repositories",
			Description: "GitHub Actions Runner Controller (ARC) pods in CrashLoopBackOff. All CI jobs queuing with no available runners.",
			Severity:    models.SeverityHigh,
			Status:      models.IncidentStatusOpen,
			Service:     "ci-cd",
			Assignee:    "",
			Timeline: []models.TimelineEvent{
				{ID: "TL-029", IncidentID: "INC-007", Type: models.TimelineEventAlertFired, Actor: "signoz", Message: "Alert fired: GitHub Actions queue depth > 50 for 15m", Metadata: map[string]string{"queue_depth": "67", "pending_jobs": "67"}, Timestamp: now.Add(-30 * time.Minute)},
				{ID: "TL-030", IncidentID: "INC-007", Type: models.TimelineEventNoteAdded, Actor: "signoz", Message: "ARC controller pods in CrashLoopBackOff. OOMKilled with 512Mi limit.", Timestamp: now.Add(-25 * time.Minute)},
			},
			RelatedAlerts: []string{"ALT-010", "ALT-011"},
			CreatedAt:     now.Add(-30 * time.Minute),
			UpdatedAt:     now.Add(-25 * time.Minute),
			Duration:      1800, // 30 min ongoing
		},
		{
			ID:          "INC-008",
			Title:       "Kafka consumer lag spike on event-processor",
			Description: "Consumer group event-processor-prod showing 500K+ lag on order-events topic. Event processing delayed by ~8 minutes.",
			Severity:    models.SeverityMedium,
			Status:      models.IncidentStatusInvestigating,
			Service:     "event-processor",
			Assignee:    "backend-team",
			Timeline: []models.TimelineEvent{
				{ID: "TL-031", IncidentID: "INC-008", Type: models.TimelineEventAlertFired, Actor: "prometheus", Message: "Alert fired: kafka_consumer_lag > 100000 for consumer group event-processor-prod", Metadata: map[string]string{"topic": "order-events", "lag": "523847"}, Timestamp: now.Add(-1*time.Hour - 15*time.Minute)},
				{ID: "TL-032", IncidentID: "INC-008", Type: models.TimelineEventAcknowledged, Actor: "backend-team", Message: "Acknowledged. Checking consumer health.", Timestamp: now.Add(-1*time.Hour - 5*time.Minute)},
				{ID: "TL-033", IncidentID: "INC-008", Type: models.TimelineEventStatusChange, Actor: "backend-team", Message: "Status changed to investigating — consumer throughput dropped after deployment", Metadata: map[string]string{"from": "open", "to": "investigating"}, Timestamp: now.Add(-55 * time.Minute)},
			},
			RelatedAlerts: []string{"ALT-012"},
			CreatedAt:     now.Add(-1*time.Hour - 15*time.Minute),
			UpdatedAt:     now.Add(-55 * time.Minute),
			Duration:      4500, // 1h 15m ongoing
		},
		{
			ID:          "INC-009",
			Title:       "S3 bucket policy misconfiguration blocking uploads",
			Description: "Integration service unable to upload documents to s3://prod-documents. AccessDenied errors after IAM policy rotation.",
			Severity:    models.SeverityMedium,
			Status:      models.IncidentStatusResolved,
			Service:     "integration-service",
			Assignee:    "infra-oncall",
			Timeline: []models.TimelineEvent{
				{ID: "TL-034", IncidentID: "INC-009", Type: models.TimelineEventAlertFired, Actor: "cloudwatch", Message: "Alert fired: S3 PutObject errors > 100/min for prod-documents bucket", Timestamp: now.Add(-10 * time.Hour)},
				{ID: "TL-035", IncidentID: "INC-009", Type: models.TimelineEventAcknowledged, Actor: "infra-oncall", Message: "Acknowledged. Correlating with recent Terraform changes.", Timestamp: now.Add(-9*time.Hour - 45*time.Minute)},
				{ID: "TL-036", IncidentID: "INC-009", Type: models.TimelineEventNoteAdded, Actor: "infra-oncall", Message: "IAM policy rotation removed s3:PutObject from integration-service role. Terraform state drift detected.", Timestamp: now.Add(-9*time.Hour - 20*time.Minute)},
				{ID: "TL-037", IncidentID: "INC-009", Type: models.TimelineEventResolved, Actor: "infra-oncall", Message: "Fixed IAM policy and applied via Terraform. Uploads resumed.", Timestamp: now.Add(-8*time.Hour - 45*time.Minute)},
			},
			RelatedAlerts: []string{"ALT-013"},
			RootCause:     "IAM policy rotation script removed s3:PutObject permission from integration-service role. Terraform state out of sync.",
			Remediation:   "Restored IAM policy via Terraform apply. Added policy validation to rotation script. Enabled Terraform drift detection.",
			CreatedAt:     now.Add(-10 * time.Hour),
			UpdatedAt:     now.Add(-8*time.Hour - 45*time.Minute),
			ResolvedAt:    ptr(now.Add(-8*time.Hour - 45*time.Minute)),
			Duration:      4500, // 1h 15m
		},
		{
			ID:          "INC-010",
			Title:       "DNS resolution failures for internal services",
			Description: "CoreDNS pods experiencing high memory pressure. Intermittent NXDOMAIN responses for *.svc.cluster.local queries.",
			Severity:    models.SeverityCritical,
			Status:      models.IncidentStatusResolved,
			Service:     "infrastructure",
			Assignee:    "platform-team",
			Timeline: []models.TimelineEvent{
				{ID: "TL-038", IncidentID: "INC-010", Type: models.TimelineEventAlertFired, Actor: "prometheus", Message: "Alert fired: CoreDNS error rate > 5% — NXDOMAIN responses for internal queries", Timestamp: now.Add(-72 * time.Hour)},
				{ID: "TL-039", IncidentID: "INC-010", Type: models.TimelineEventAcknowledged, Actor: "platform-team", Message: "Acknowledged. Multiple services reporting DNS failures.", Timestamp: now.Add(-71*time.Hour - 50*time.Minute)},
				{ID: "TL-040", IncidentID: "INC-010", Type: models.TimelineEventEscalated, Actor: "platform-team", Message: "Escalated to SEV1 — widespread impact across all services", Timestamp: now.Add(-71*time.Hour - 45*time.Minute)},
				{ID: "TL-041", IncidentID: "INC-010", Type: models.TimelineEventNoteAdded, Actor: "platform-team", Message: "CoreDNS cache plugin consuming 2Gi memory. Increased memory limit and scaled to 5 replicas.", Timestamp: now.Add(-71 * time.Hour)},
				{ID: "TL-042", IncidentID: "INC-010", Type: models.TimelineEventResolved, Actor: "platform-team", Message: "DNS resolution stable. CoreDNS cache TTL reduced from 300s to 30s, memory limits increased to 1Gi per pod.", Timestamp: now.Add(-70*time.Hour - 15*time.Minute)},
			},
			RelatedAlerts: []string{"ALT-014", "ALT-015", "ALT-016"},
			RootCause:     "CoreDNS cache plugin default configuration caused unbounded memory growth under high query volume.",
			Remediation:   "Reduced CoreDNS cache TTL to 30s. Increased memory limits to 1Gi. Scaled to 5 replicas with pod anti-affinity. Added memory-based HPA.",
			CreatedAt:     now.Add(-72 * time.Hour),
			UpdatedAt:     now.Add(-70*time.Hour - 15*time.Minute),
			ResolvedAt:    ptr(now.Add(-70*time.Hour - 15*time.Minute)),
			Duration:      6300, // 1h 45m
		},
	}
}

// Alerts returns 20 realistic mock alerts from varied sources.
func Alerts() []models.Alert {
	return []models.Alert{
		{ID: "ALT-001", Source: models.AlertSourceSigNoz, Title: "PaymentHighErrorRate", Description: "Payment service error rate above 10% threshold", Severity: models.SeverityCritical, Service: "payment-service", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "PaymentHighErrorRate", "severity": "critical", "namespace": "prod"}, Annotations: map[string]string{"summary": "Payment error rate 15.3%", "runbook": "https://runbooks.aegis.dev/payment-errors"}, StartsAt: now.Add(-3*time.Hour - 30*time.Minute), Fingerprint: "fp-payment-error-001"},
		{ID: "ALT-002", Source: models.AlertSourceSigNoz, Title: "PaymentLatencyHigh", Description: "Payment service P99 latency above 2s", Severity: models.SeverityHigh, Service: "payment-service", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "PaymentLatencyHigh", "severity": "high", "namespace": "prod"}, StartsAt: now.Add(-3 * time.Hour), Fingerprint: "fp-payment-latency-001"},
		{ID: "ALT-003", Source: models.AlertSourcePrometheus, Title: "HighLatency", Description: "user-service /api/v1/profile P99 > 1s", Severity: models.SeverityHigh, Service: "user-service", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "HighLatency", "endpoint": "/api/v1/profile", "service": "user-service"}, StartsAt: now.Add(-2 * time.Hour), Fingerprint: "fp-user-latency-001"},
		{ID: "ALT-004", Source: models.AlertSourcePrometheus, Title: "KubeNodeNotReady", Description: "Node i-0abc123 is NotReady", Severity: models.SeverityMedium, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"alertname": "KubeNodeNotReady", "node": "i-0abc123"}, StartsAt: now.Add(-22 * time.Hour), EndsAt: ptr(now.Add(-19*time.Hour - 15*time.Minute)), Fingerprint: "fp-node-notready-001"},
		{ID: "ALT-005", Source: models.AlertSourcePrometheus, Title: "KubePodCrashLooping", Description: "logging-sidecar CrashLoopBackOff on i-0abc123", Severity: models.SeverityMedium, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"alertname": "KubePodCrashLooping", "pod": "logging-sidecar-xyz", "node": "i-0abc123"}, StartsAt: now.Add(-22 * time.Hour), EndsAt: ptr(now.Add(-20 * time.Hour)), Fingerprint: "fp-crashloop-001"},
		{ID: "ALT-006", Source: models.AlertSourcePrometheus, Title: "CertExpiryWarning", Description: "TLS certificate for api.aegis.dev expires in 7 days", Severity: models.SeverityLow, Service: "gateway", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "CertExpiryWarning", "domain": "api.aegis.dev", "days_remaining": "7"}, StartsAt: now.Add(-6 * time.Hour), Fingerprint: "fp-cert-expiry-001"},
		{ID: "ALT-007", Source: models.AlertSourceCloudWatch, Title: "RDSHighConnections", Description: "Aurora connections at 97.5% of max", Severity: models.SeverityCritical, Service: "order-service", Status: models.AlertStatusResolved, Labels: map[string]string{"db_instance": "prod-orders-primary", "metric": "DatabaseConnections"}, StartsAt: now.Add(-26 * time.Hour), EndsAt: ptr(now.Add(-24 * time.Hour)), Fingerprint: "fp-rds-connections-001"},
		{ID: "ALT-008", Source: models.AlertSourceCloudWatch, Title: "RDSCPUUtilization", Description: "Aurora CPU above 85%", Severity: models.SeverityHigh, Service: "order-service", Status: models.AlertStatusResolved, Labels: map[string]string{"db_instance": "prod-orders-primary", "metric": "CPUUtilization"}, StartsAt: now.Add(-26 * time.Hour), EndsAt: ptr(now.Add(-24*time.Hour - 30*time.Minute)), Fingerprint: "fp-rds-cpu-001"},
		{ID: "ALT-009", Source: models.AlertSourceCloudWatch, Title: "ElastiCacheFailover", Description: "Redis primary node failed health check, failover initiated", Severity: models.SeverityHigh, Service: "cache-layer", Status: models.AlertStatusResolved, Labels: map[string]string{"cluster": "prod-sessions", "event": "failover"}, StartsAt: now.Add(-48 * time.Hour), EndsAt: ptr(now.Add(-47 * time.Hour)), Fingerprint: "fp-redis-failover-001"},
		{ID: "ALT-010", Source: models.AlertSourceSigNoz, Title: "GHAQueueDepth", Description: "GitHub Actions job queue depth above 50", Severity: models.SeverityHigh, Service: "ci-cd", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "GHAQueueDepth", "queue_depth": "67"}, StartsAt: now.Add(-30 * time.Minute), Fingerprint: "fp-gha-queue-001"},
		{ID: "ALT-011", Source: models.AlertSourcePrometheus, Title: "KubePodCrashLooping", Description: "ARC controller pod in CrashLoopBackOff", Severity: models.SeverityHigh, Service: "ci-cd", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "KubePodCrashLooping", "pod": "arc-controller-0", "reason": "OOMKilled"}, StartsAt: now.Add(-28 * time.Minute), Fingerprint: "fp-arc-crashloop-001"},
		{ID: "ALT-012", Source: models.AlertSourcePrometheus, Title: "KafkaConsumerLag", Description: "Consumer lag > 100K on event-processor-prod", Severity: models.SeverityMedium, Service: "event-processor", Status: models.AlertStatusFiring, Labels: map[string]string{"alertname": "KafkaConsumerLag", "consumer_group": "event-processor-prod", "topic": "order-events"}, StartsAt: now.Add(-1*time.Hour - 15*time.Minute), Fingerprint: "fp-kafka-lag-001"},
		{ID: "ALT-013", Source: models.AlertSourceCloudWatch, Title: "S3AccessDenied", Description: "S3 PutObject errors > 100/min on prod-documents", Severity: models.SeverityMedium, Service: "integration-service", Status: models.AlertStatusResolved, Labels: map[string]string{"bucket": "prod-documents", "error_code": "AccessDenied"}, StartsAt: now.Add(-10 * time.Hour), EndsAt: ptr(now.Add(-8*time.Hour - 45*time.Minute)), Fingerprint: "fp-s3-denied-001"},
		{ID: "ALT-014", Source: models.AlertSourcePrometheus, Title: "CoreDNSErrorRate", Description: "CoreDNS error rate above 5%", Severity: models.SeverityCritical, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"alertname": "CoreDNSErrorRate"}, StartsAt: now.Add(-72 * time.Hour), EndsAt: ptr(now.Add(-70*time.Hour - 15*time.Minute)), Fingerprint: "fp-dns-error-001"},
		{ID: "ALT-015", Source: models.AlertSourcePrometheus, Title: "CoreDNSMemoryHigh", Description: "CoreDNS memory usage above 80%", Severity: models.SeverityHigh, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"alertname": "CoreDNSMemoryHigh", "pod": "coredns-abc"}, StartsAt: now.Add(-72 * time.Hour), EndsAt: ptr(now.Add(-71 * time.Hour)), Fingerprint: "fp-dns-memory-001"},
		{ID: "ALT-016", Source: models.AlertSourceSigNoz, Title: "ServiceDiscoveryFailure", Description: "Multiple services failing DNS resolution for internal endpoints", Severity: models.SeverityCritical, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"alertname": "ServiceDiscoveryFailure", "affected_services": "12"}, StartsAt: now.Add(-71*time.Hour - 50*time.Minute), EndsAt: ptr(now.Add(-70*time.Hour - 15*time.Minute)), Fingerprint: "fp-svc-discovery-001"},
		{ID: "ALT-017", Source: models.AlertSourceDatadog, Title: "APMErrorRateSpike", Description: "auth-service error rate increased 300% in last 15 minutes", Severity: models.SeverityMedium, Service: "auth-service", Status: models.AlertStatusResolved, Labels: map[string]string{"service": "auth-service", "env": "production"}, StartsAt: now.Add(-36 * time.Hour), EndsAt: ptr(now.Add(-35 * time.Hour)), Fingerprint: "fp-apm-error-001"},
		{ID: "ALT-018", Source: models.AlertSourceDatadog, Title: "InfraHostHighCPU", Description: "Host cpu.usage > 90% for 10 minutes", Severity: models.SeverityMedium, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"host": "worker-node-04", "cpu_usage": "93%"}, StartsAt: now.Add(-60 * time.Hour), EndsAt: ptr(now.Add(-59*time.Hour - 30*time.Minute)), Fingerprint: "fp-host-cpu-001"},
		{ID: "ALT-019", Source: models.AlertSourcePrometheus, Title: "EtcdHighLatency", Description: "etcd request latency P99 above 200ms", Severity: models.SeverityHigh, Service: "infrastructure", Status: models.AlertStatusResolved, Labels: map[string]string{"alertname": "EtcdHighLatency", "cluster": "prod-eks"}, StartsAt: now.Add(-96 * time.Hour), EndsAt: ptr(now.Add(-95 * time.Hour)), Fingerprint: "fp-etcd-latency-001"},
		{ID: "ALT-020", Source: models.AlertSourceCloudWatch, Title: "LambdaThrottling", Description: "Lambda function notification-sender throttled", Severity: models.SeverityLow, Service: "notification-service", Status: models.AlertStatusResolved, Labels: map[string]string{"function": "notification-sender", "throttled_invocations": "45"}, StartsAt: now.Add(-84 * time.Hour), EndsAt: ptr(now.Add(-83*time.Hour - 45*time.Minute)), Fingerprint: "fp-lambda-throttle-001"},
	}
}
