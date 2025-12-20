// ---- Types ----

export type IncidentSeverity = "critical" | "high" | "medium" | "low"
export type IncidentStatus =
  | "open"
  | "investigating"
  | "identified"
  | "monitoring"
  | "resolved"

export type TimelineEventType =
  | "alert_fired"
  | "acknowledged"
  | "status_change"
  | "note_added"
  | "escalated"
  | "resolved"

export type AlertSource = "signoz" | "datadog" | "prometheus"

export interface TimelineEvent {
  id: string
  type: TimelineEventType
  timestamp: string
  actor: string
  message: string
  metadata?: Record<string, string>
}

export interface RelatedAlert {
  id: string
  title: string
  source: AlertSource
  severity: IncidentSeverity
  firedAt: string
  service: string
}

export interface Incident {
  id: string
  title: string
  description: string
  severity: IncidentSeverity
  status: IncidentStatus
  service: string
  affectedServices: string[]
  assignee: string
  createdAt: string
  updatedAt: string
  resolvedAt?: string
  timeline: TimelineEvent[]
  relatedAlerts: RelatedAlert[]
}

export interface AlertFeedItem {
  id: string
  title: string
  source: AlertSource
  severity: IncidentSeverity
  service: string
  firedAt: string
  dedupKey: string
  incidentId?: string
}

// ---- Helpers ----

function hoursAgo(h: number): string {
  const d = new Date()
  d.setHours(d.getHours() - h)
  return d.toISOString()
}

function minutesAgo(m: number): string {
  const d = new Date()
  d.setMinutes(d.getMinutes() - m)
  return d.toISOString()
}

function daysAgo(days: number, hours = 0): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  d.setHours(d.getHours() - hours)
  return d.toISOString()
}

// ---- Incidents ----

export const MOCK_INCIDENTS: Incident[] = [
  // CRITICAL - Open
  {
    id: "INC-1301",
    title: "Payment processing timeout",
    description:
      "Payment gateway returning 504 errors for 30%+ of transactions. Revenue impact confirmed. Multiple upstream timeouts traced to connection pool saturation on payment-service pods.",
    severity: "critical",
    status: "open",
    service: "payment-service",
    affectedServices: ["payment-service", "api-gateway", "notification-service"],
    assignee: "Sarah Chen",
    createdAt: minutesAgo(23),
    updatedAt: minutesAgo(5),
    timeline: [
      {
        id: "tl-1301-1",
        type: "alert_fired",
        timestamp: minutesAgo(23),
        actor: "SigNoz",
        message:
          "Alert: payment-service p99 latency > 5000ms (current: 8420ms)",
      },
      {
        id: "tl-1301-2",
        type: "alert_fired",
        timestamp: minutesAgo(22),
        actor: "Prometheus",
        message:
          "Alert: payment_gateway_error_rate > 30% (current: 34.2%)",
      },
      {
        id: "tl-1301-3",
        type: "acknowledged",
        timestamp: minutesAgo(20),
        actor: "Sarah Chen",
        message: "Acknowledged. Looking at payment-service dashboards now.",
      },
      {
        id: "tl-1301-4",
        type: "note_added",
        timestamp: minutesAgo(15),
        actor: "Sarah Chen",
        message:
          "Connection pool maxed at 200. Seeing ETIMEDOUT on downstream calls to Stripe API. Checking if this is a Stripe incident.",
      },
      {
        id: "tl-1301-5",
        type: "escalated",
        timestamp: minutesAgo(10),
        actor: "Sarah Chen",
        message:
          "Escalated to P1. Confirmed revenue impact: ~$45K/hr. Paging Commerce on-call.",
      },
      {
        id: "tl-1301-6",
        type: "note_added",
        timestamp: minutesAgo(5),
        actor: "James Park",
        message:
          "Stripe status page shows degraded API performance in us-east-1. Increasing connection pool to 500 and adding retry with backoff.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2001",
        title: "payment-service p99 latency > 5000ms",
        source: "signoz",
        severity: "critical",
        firedAt: minutesAgo(23),
        service: "payment-service",
      },
      {
        id: "alert-2002",
        title: "payment_gateway_error_rate > 30%",
        source: "prometheus",
        severity: "critical",
        firedAt: minutesAgo(22),
        service: "payment-service",
      },
      {
        id: "alert-2003",
        title: "api-gateway 5xx spike on /checkout",
        source: "datadog",
        severity: "high",
        firedAt: minutesAgo(21),
        service: "api-gateway",
      },
    ],
  },

  // CRITICAL - Investigating
  {
    id: "INC-1299",
    title: "Database connection pool exhausted",
    description:
      "Aurora PostgreSQL primary instance connection limit reached. auth-service and user-service returning 503s. Active connections stuck at 500/500.",
    severity: "critical",
    status: "investigating",
    service: "auth-service",
    affectedServices: ["auth-service", "user-service", "api-gateway"],
    assignee: "Mike Rodriguez",
    createdAt: hoursAgo(2),
    updatedAt: minutesAgo(12),
    timeline: [
      {
        id: "tl-1299-1",
        type: "alert_fired",
        timestamp: hoursAgo(2),
        actor: "Prometheus",
        message:
          "Alert: rds_connections_used > 95% (current: 98%) on aurora-primary-01",
      },
      {
        id: "tl-1299-2",
        type: "alert_fired",
        timestamp: hoursAgo(2),
        actor: "SigNoz",
        message: "Alert: auth-service error rate > 10% (current: 28.5%)",
      },
      {
        id: "tl-1299-3",
        type: "acknowledged",
        timestamp: hoursAgo(1.8),
        actor: "Mike Rodriguez",
        message:
          "On it. Checking RDS console and connection pool configurations.",
      },
      {
        id: "tl-1299-4",
        type: "status_change",
        timestamp: hoursAgo(1.5),
        actor: "Mike Rodriguez",
        message: "Status changed to Investigating",
        metadata: { from: "open", to: "investigating" },
      },
      {
        id: "tl-1299-5",
        type: "note_added",
        timestamp: hoursAgo(1),
        actor: "Mike Rodriguez",
        message:
          "Found long-running queries from user-service batch job. 120+ connections held for >10min each. Killing idle connections and investigating the batch job.",
      },
      {
        id: "tl-1299-6",
        type: "escalated",
        timestamp: minutesAgo(45),
        actor: "Mike Rodriguez",
        message:
          "Escalated to DB team. Need to increase max_connections and add PgBouncer.",
      },
      {
        id: "tl-1299-7",
        type: "note_added",
        timestamp: minutesAgo(12),
        actor: "Lisa Wang",
        message:
          "Killed 80 idle connections. Pool back to 380/500. Error rate dropping. Working on PgBouncer deployment.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2010",
        title: "RDS connections > 95%",
        source: "prometheus",
        severity: "critical",
        firedAt: hoursAgo(2),
        service: "auth-service",
      },
      {
        id: "alert-2011",
        title: "auth-service error rate > 10%",
        source: "signoz",
        severity: "critical",
        firedAt: hoursAgo(2),
        service: "auth-service",
      },
      {
        id: "alert-2012",
        title: "user-service 503 rate elevated",
        source: "datadog",
        severity: "high",
        firedAt: hoursAgo(1.9),
        service: "user-service",
      },
    ],
  },

  // HIGH - Identified
  {
    id: "INC-1295",
    title: "Memory leak in auth-service",
    description:
      "auth-service pods OOMKilled every 4-6 hours. Heap grows linearly from 512MB to 2GB. Suspected leak in token cache module.",
    severity: "high",
    status: "identified",
    service: "auth-service",
    affectedServices: ["auth-service"],
    assignee: "Lisa Wang",
    createdAt: daysAgo(1, 6),
    updatedAt: hoursAgo(3),
    timeline: [
      {
        id: "tl-1295-1",
        type: "alert_fired",
        timestamp: daysAgo(1, 6),
        actor: "Prometheus",
        message:
          "Alert: auth-service container memory > 90% (current: 92%)",
      },
      {
        id: "tl-1295-2",
        type: "acknowledged",
        timestamp: daysAgo(1, 5),
        actor: "Lisa Wang",
        message: "Acknowledged. Checking pod metrics.",
      },
      {
        id: "tl-1295-3",
        type: "status_change",
        timestamp: daysAgo(1, 4),
        actor: "Lisa Wang",
        message: "Status changed to Investigating",
        metadata: { from: "open", to: "investigating" },
      },
      {
        id: "tl-1295-4",
        type: "note_added",
        timestamp: daysAgo(1, 2),
        actor: "Lisa Wang",
        message:
          "Heap dump shows token cache growing unbounded. The eviction policy was disabled in v1.8.3. Creating fix PR.",
      },
      {
        id: "tl-1295-5",
        type: "status_change",
        timestamp: daysAgo(1),
        actor: "Lisa Wang",
        message: "Status changed to Identified. Root cause: disabled cache eviction in v1.8.3.",
        metadata: { from: "investigating", to: "identified" },
      },
      {
        id: "tl-1295-6",
        type: "note_added",
        timestamp: hoursAgo(3),
        actor: "Lisa Wang",
        message:
          "Fix PR #482 merged. Deploying to staging for validation. Will deploy to prod in next window.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2020",
        title: "auth-service container memory > 90%",
        source: "prometheus",
        severity: "high",
        firedAt: daysAgo(1, 6),
        service: "auth-service",
      },
      {
        id: "alert-2021",
        title: "auth-service OOMKilled",
        source: "signoz",
        severity: "high",
        firedAt: daysAgo(1, 4),
        service: "auth-service",
      },
    ],
  },

  // HIGH - Monitoring
  {
    id: "INC-1292",
    title: "Notification delivery delays > 30s",
    description:
      "Email and push notification delivery latency spiked to 30-60s. Root cause: SQS queue backpressure from increased signup traffic.",
    severity: "high",
    status: "monitoring",
    service: "notification-service",
    affectedServices: ["notification-service"],
    assignee: "David Kim",
    createdAt: daysAgo(2, 8),
    updatedAt: hoursAgo(6),
    timeline: [
      {
        id: "tl-1292-1",
        type: "alert_fired",
        timestamp: daysAgo(2, 8),
        actor: "Datadog",
        message:
          "Alert: notification_delivery_latency_p99 > 30s (current: 42s)",
      },
      {
        id: "tl-1292-2",
        type: "acknowledged",
        timestamp: daysAgo(2, 7),
        actor: "David Kim",
        message: "Acknowledged. Investigating SQS queue depth.",
      },
      {
        id: "tl-1292-3",
        type: "status_change",
        timestamp: daysAgo(2, 5),
        actor: "David Kim",
        message: "Status changed to Identified. SQS consumer throughput insufficient.",
        metadata: { from: "investigating", to: "identified" },
      },
      {
        id: "tl-1292-4",
        type: "note_added",
        timestamp: daysAgo(2, 3),
        actor: "David Kim",
        message:
          "Scaled consumer fleet from 3 to 8 pods. Queue depth dropping steadily.",
      },
      {
        id: "tl-1292-5",
        type: "status_change",
        timestamp: daysAgo(1, 12),
        actor: "David Kim",
        message: "Status changed to Monitoring. Delivery latency back to <5s.",
        metadata: { from: "identified", to: "monitoring" },
      },
      {
        id: "tl-1292-6",
        type: "note_added",
        timestamp: hoursAgo(6),
        actor: "David Kim",
        message:
          "Latency stable at 2-3s for 24h. Will resolve after 48h observation window.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2030",
        title: "notification_delivery_latency_p99 > 30s",
        source: "datadog",
        severity: "high",
        firedAt: daysAgo(2, 8),
        service: "notification-service",
      },
    ],
  },

  // HIGH - Resolved
  {
    id: "INC-1288",
    title: "API Gateway rate limiter misconfiguration",
    description:
      "Rate limiter on /api/v2 endpoints was set to 10 req/s instead of 10000 req/s after config deployment. Caused widespread 429 errors.",
    severity: "high",
    status: "resolved",
    service: "api-gateway",
    affectedServices: ["api-gateway"],
    assignee: "Sarah Chen",
    createdAt: daysAgo(5, 3),
    updatedAt: daysAgo(5, 1),
    resolvedAt: daysAgo(5, 1),
    timeline: [
      {
        id: "tl-1288-1",
        type: "alert_fired",
        timestamp: daysAgo(5, 3),
        actor: "SigNoz",
        message: "Alert: api-gateway 429 rate > 5% (current: 68%)",
      },
      {
        id: "tl-1288-2",
        type: "acknowledged",
        timestamp: daysAgo(5, 3),
        actor: "Sarah Chen",
        message: "Acknowledged immediately. Obvious rate limiter issue.",
      },
      {
        id: "tl-1288-3",
        type: "status_change",
        timestamp: daysAgo(5, 2.5),
        actor: "Sarah Chen",
        message: "Identified: rate_limit_per_second set to 10 instead of 10000 in configmap.",
        metadata: { from: "open", to: "identified" },
      },
      {
        id: "tl-1288-4",
        type: "note_added",
        timestamp: daysAgo(5, 2),
        actor: "Sarah Chen",
        message: "Config reverted. Rate limiter functioning normally.",
      },
      {
        id: "tl-1288-5",
        type: "resolved",
        timestamp: daysAgo(5, 1),
        actor: "Sarah Chen",
        message: "Resolved. Added validation webhook for rate limiter configs. Postmortem scheduled.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2040",
        title: "api-gateway 429 rate > 5%",
        source: "signoz",
        severity: "high",
        firedAt: daysAgo(5, 3),
        service: "api-gateway",
      },
    ],
  },

  // MEDIUM - Open
  {
    id: "INC-1300",
    title: "Certificate expiring in 7 days",
    description:
      "TLS certificate for *.aegis.internal expiring on April 17th. Auto-renewal via cert-manager failed due to DNS challenge timeout.",
    severity: "medium",
    status: "open",
    service: "deployment-controller",
    affectedServices: ["deployment-controller", "api-gateway"],
    assignee: "James Park",
    createdAt: hoursAgo(8),
    updatedAt: hoursAgo(4),
    timeline: [
      {
        id: "tl-1300-1",
        type: "alert_fired",
        timestamp: hoursAgo(8),
        actor: "Prometheus",
        message:
          "Alert: tls_certificate_expiry_days < 7 for *.aegis.internal",
      },
      {
        id: "tl-1300-2",
        type: "acknowledged",
        timestamp: hoursAgo(7),
        actor: "James Park",
        message:
          "Acknowledged. Checking cert-manager logs for renewal failure.",
      },
      {
        id: "tl-1300-3",
        type: "note_added",
        timestamp: hoursAgo(4),
        actor: "James Park",
        message:
          "cert-manager DNS01 challenge failing. Route53 IAM role missing dns:ChangeResourceRecordSets permission. Creating PR for Terraform fix.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2050",
        title: "TLS certificate expiry < 7 days",
        source: "prometheus",
        severity: "medium",
        firedAt: hoursAgo(8),
        service: "deployment-controller",
      },
    ],
  },

  // MEDIUM - Open
  {
    id: "INC-1298",
    title: "Elevated 5xx on user-service /profile endpoint",
    description:
      "Intermittent 500 errors on GET /profile for users with special characters in display names. Error rate ~2%.",
    severity: "medium",
    status: "open",
    service: "user-service",
    affectedServices: ["user-service"],
    assignee: "Alex Turner",
    createdAt: daysAgo(1, 2),
    updatedAt: daysAgo(0, 18),
    timeline: [
      {
        id: "tl-1298-1",
        type: "alert_fired",
        timestamp: daysAgo(1, 2),
        actor: "SigNoz",
        message: "Alert: user-service /profile 5xx rate > 1% (current: 2.1%)",
      },
      {
        id: "tl-1298-2",
        type: "acknowledged",
        timestamp: daysAgo(1, 1),
        actor: "Alex Turner",
        message: "Acknowledged. Investigating error patterns.",
      },
      {
        id: "tl-1298-3",
        type: "note_added",
        timestamp: daysAgo(0, 18),
        actor: "Alex Turner",
        message:
          "Traced to unicode normalization bug in display name serialization. Only affects ~500 users. Low urgency, fix scheduled for next sprint.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2060",
        title: "user-service /profile 5xx > 1%",
        source: "signoz",
        severity: "medium",
        firedAt: daysAgo(1, 2),
        service: "user-service",
      },
    ],
  },

  // MEDIUM - Resolved
  {
    id: "INC-1285",
    title: "Deployment pipeline flaky tests",
    description:
      "CI pipeline for payment-service failing ~20% of runs due to flaky integration tests. Tests depend on external sandbox that has intermittent connectivity.",
    severity: "medium",
    status: "resolved",
    service: "deployment-controller",
    affectedServices: ["deployment-controller"],
    assignee: "Mike Rodriguez",
    createdAt: daysAgo(7),
    updatedAt: daysAgo(4),
    resolvedAt: daysAgo(4),
    timeline: [
      {
        id: "tl-1285-1",
        type: "alert_fired",
        timestamp: daysAgo(7),
        actor: "Datadog",
        message:
          "Alert: ci_pipeline_failure_rate > 15% for payment-service (current: 22%)",
      },
      {
        id: "tl-1285-2",
        type: "acknowledged",
        timestamp: daysAgo(7),
        actor: "Mike Rodriguez",
        message: "Looking into it.",
      },
      {
        id: "tl-1285-3",
        type: "note_added",
        timestamp: daysAgo(6),
        actor: "Mike Rodriguez",
        message:
          "Identified flaky tests: payment_integration_test.go lines 142-198. External sandbox returns 503 intermittently.",
      },
      {
        id: "tl-1285-4",
        type: "resolved",
        timestamp: daysAgo(4),
        actor: "Mike Rodriguez",
        message: "Fixed by adding WireMock stubs for external sandbox. Pipeline pass rate back to 98%.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2070",
        title: "CI pipeline failure rate > 15%",
        source: "datadog",
        severity: "medium",
        firedAt: daysAgo(7),
        service: "deployment-controller",
      },
    ],
  },

  // LOW - Resolved
  {
    id: "INC-1280",
    title: "Grafana dashboard query timeout",
    description:
      "SLO dashboard in Grafana timing out due to unoptimized PromQL query across 90-day window. Dashboard renders blank for some panels.",
    severity: "low",
    status: "resolved",
    service: "deployment-controller",
    affectedServices: [],
    assignee: "David Kim",
    createdAt: daysAgo(10),
    updatedAt: daysAgo(8),
    resolvedAt: daysAgo(8),
    timeline: [
      {
        id: "tl-1280-1",
        type: "alert_fired",
        timestamp: daysAgo(10),
        actor: "Datadog",
        message: "Alert: grafana_query_timeout on SLO dashboard panel",
      },
      {
        id: "tl-1280-2",
        type: "acknowledged",
        timestamp: daysAgo(10),
        actor: "David Kim",
        message: "Will optimize the query.",
      },
      {
        id: "tl-1280-3",
        type: "resolved",
        timestamp: daysAgo(8),
        actor: "David Kim",
        message:
          "Replaced subquery with recording rule. Dashboard loads in <2s now.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2080",
        title: "Grafana query timeout",
        source: "datadog",
        severity: "low",
        firedAt: daysAgo(10),
        service: "deployment-controller",
      },
    ],
  },

  // LOW - Resolved
  {
    id: "INC-1278",
    title: "Log volume spike from debug logging",
    description:
      "notification-service accidentally deployed with DEBUG log level. Log volume 10x normal, inflating storage costs.",
    severity: "low",
    status: "resolved",
    service: "notification-service",
    affectedServices: ["notification-service"],
    assignee: "Alex Turner",
    createdAt: daysAgo(12),
    updatedAt: daysAgo(11),
    resolvedAt: daysAgo(11),
    timeline: [
      {
        id: "tl-1278-1",
        type: "alert_fired",
        timestamp: daysAgo(12),
        actor: "Prometheus",
        message:
          "Alert: log_bytes_per_second > 50MB/s for notification-service (current: 82MB/s)",
      },
      {
        id: "tl-1278-2",
        type: "acknowledged",
        timestamp: daysAgo(12),
        actor: "Alex Turner",
        message: "Checking log level config.",
      },
      {
        id: "tl-1278-3",
        type: "note_added",
        timestamp: daysAgo(12),
        actor: "Alex Turner",
        message:
          "Confirmed: LOG_LEVEL=DEBUG set in v0.9.5 configmap. Should be INFO.",
      },
      {
        id: "tl-1278-4",
        type: "resolved",
        timestamp: daysAgo(11),
        actor: "Alex Turner",
        message:
          "Log level reverted to INFO. Added CI check to prevent DEBUG in production configs.",
      },
    ],
    relatedAlerts: [
      {
        id: "alert-2090",
        title: "Log volume > 50MB/s",
        source: "prometheus",
        severity: "low",
        firedAt: daysAgo(12),
        service: "notification-service",
      },
    ],
  },
]

// ---- Alert Feed ----

export const MOCK_ALERT_FEED: AlertFeedItem[] = [
  {
    id: "af-001",
    title: "payment-service p99 latency > 5000ms",
    source: "signoz",
    severity: "critical",
    service: "payment-service",
    firedAt: minutesAgo(23),
    dedupKey: "payment-latency-p99",
    incidentId: "INC-1301",
  },
  {
    id: "af-002",
    title: "payment_gateway_error_rate > 30%",
    source: "prometheus",
    severity: "critical",
    service: "payment-service",
    firedAt: minutesAgo(22),
    dedupKey: "payment-error-rate",
    incidentId: "INC-1301",
  },
  {
    id: "af-003",
    title: "api-gateway 5xx spike on /checkout",
    source: "datadog",
    severity: "high",
    service: "api-gateway",
    firedAt: minutesAgo(21),
    dedupKey: "apigw-5xx-checkout",
    incidentId: "INC-1301",
  },
  {
    id: "af-004",
    title: "RDS connections > 95% on aurora-primary-01",
    source: "prometheus",
    severity: "critical",
    service: "auth-service",
    firedAt: hoursAgo(2),
    dedupKey: "rds-connections-95",
    incidentId: "INC-1299",
  },
  {
    id: "af-005",
    title: "auth-service error rate > 10%",
    source: "signoz",
    severity: "critical",
    service: "auth-service",
    firedAt: hoursAgo(2),
    dedupKey: "auth-error-rate",
    incidentId: "INC-1299",
  },
  {
    id: "af-006",
    title: "user-service 503 rate elevated",
    source: "datadog",
    severity: "high",
    service: "user-service",
    firedAt: hoursAgo(1.9),
    dedupKey: "user-503-rate",
    incidentId: "INC-1299",
  },
  {
    id: "af-007",
    title: "TLS certificate expiry < 7 days",
    source: "prometheus",
    severity: "medium",
    service: "deployment-controller",
    firedAt: hoursAgo(8),
    dedupKey: "tls-cert-expiry",
    incidentId: "INC-1300",
  },
  {
    id: "af-008",
    title: "notification-service queue depth > 10000",
    source: "datadog",
    severity: "medium",
    service: "notification-service",
    firedAt: hoursAgo(5),
    dedupKey: "notif-queue-depth",
  },
  {
    id: "af-009",
    title: "CPU utilization > 80% on api-gateway pods",
    source: "prometheus",
    severity: "medium",
    service: "api-gateway",
    firedAt: hoursAgo(3),
    dedupKey: "apigw-cpu-80",
  },
  {
    id: "af-010",
    title: "Disk usage > 85% on logging volume",
    source: "prometheus",
    severity: "medium",
    service: "deployment-controller",
    firedAt: hoursAgo(6),
    dedupKey: "disk-usage-85",
  },
  {
    id: "af-011",
    title: "Slow query detected on user-service (>2s)",
    source: "signoz",
    severity: "low",
    service: "user-service",
    firedAt: hoursAgo(4),
    dedupKey: "user-slow-query",
  },
  {
    id: "af-012",
    title: "auth-service container memory > 90%",
    source: "prometheus",
    severity: "high",
    service: "auth-service",
    firedAt: daysAgo(1, 6),
    dedupKey: "auth-memory-90",
    incidentId: "INC-1295",
  },
  {
    id: "af-013",
    title: "Deployment rollback detected: notification-service",
    source: "datadog",
    severity: "medium",
    service: "notification-service",
    firedAt: daysAgo(1),
    dedupKey: "notif-rollback",
  },
  {
    id: "af-014",
    title: "Pod restart count > 5 in 1h: auth-service",
    source: "prometheus",
    severity: "high",
    service: "auth-service",
    firedAt: hoursAgo(12),
    dedupKey: "auth-pod-restarts",
    incidentId: "INC-1295",
  },
  {
    id: "af-015",
    title: "HTTP 4xx rate > 5% on user-service",
    source: "signoz",
    severity: "low",
    service: "user-service",
    firedAt: hoursAgo(10),
    dedupKey: "user-4xx-rate",
  },
  {
    id: "af-016",
    title: "payment-service pod CrashLoopBackOff",
    source: "prometheus",
    severity: "high",
    service: "payment-service",
    firedAt: minutesAgo(18),
    dedupKey: "payment-crashloop",
    incidentId: "INC-1301",
  },
  {
    id: "af-017",
    title: "DNS resolution latency > 500ms",
    source: "datadog",
    severity: "low",
    service: "api-gateway",
    firedAt: hoursAgo(7),
    dedupKey: "dns-latency",
  },
  {
    id: "af-018",
    title: "Config drift detected on auth-service",
    source: "signoz",
    severity: "low",
    service: "auth-service",
    firedAt: daysAgo(2),
    dedupKey: "auth-config-drift",
  },
]

// ---- Lookup helpers ----

export function getIncidentById(id: string): Incident | undefined {
  return MOCK_INCIDENTS.find((inc) => inc.id === id)
}

export function getIncidentsByStatus(status: IncidentStatus): Incident[] {
  return MOCK_INCIDENTS.filter((inc) => inc.status === status)
}

export function getIncidentsBySeverity(severity: IncidentSeverity): Incident[] {
  return MOCK_INCIDENTS.filter((inc) => inc.severity === severity)
}

export function getActiveIncidents(): Incident[] {
  return MOCK_INCIDENTS.filter((inc) => inc.status !== "resolved")
}

export const SEVERITY_ORDER: Record<IncidentSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

export const ASSIGNEES = [
  "Sarah Chen",
  "Mike Rodriguez",
  "Lisa Wang",
  "David Kim",
  "James Park",
  "Alex Turner",
]

export const INCIDENT_SERVICES = [
  "api-gateway",
  "auth-service",
  "payment-service",
  "user-service",
  "notification-service",
  "deployment-controller",
]
