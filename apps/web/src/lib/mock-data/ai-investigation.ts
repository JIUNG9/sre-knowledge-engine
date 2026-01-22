// ---- Types ----

export type ToolStatus = "succeeded" | "failed" | "pending"
export type RiskLevel = "low" | "medium" | "high"
export type StepApproval = "approved" | "rejected" | "pending"

export interface MCPToolCall {
  id: string
  toolName: string
  description: string
  status: ToolStatus
  durationMs: number
  input?: string
  output?: string
}

export interface RemediationStep {
  id: string
  order: number
  description: string
  command: string
  riskLevel: RiskLevel
  approval: StepApproval
  estimatedImpact: string
}

export interface TokenUsage {
  input: number
  output: number
  cached: number
  estimatedCost: number
}

export interface InvestigationMessage {
  id: string
  role: "user" | "assistant" | "tool"
  content: string
  timestamp: string
  toolCall?: MCPToolCall
  isCollapsible?: boolean
}

export interface AIInvestigation {
  id: string
  incidentId: string
  status: "running" | "completed" | "failed"
  startedAt: string
  completedAt?: string
  durationSeconds: number
  confidenceScore: number
  summary: string
  rootCause: string
  affectedServices: string[]
  remediationSteps: RemediationStep[]
  toolCalls: MCPToolCall[]
  tokenUsage: TokenUsage
  messages: InvestigationMessage[]
}

// ---- Helpers ----

function minutesAgo(m: number): string {
  const d = new Date()
  d.setMinutes(d.getMinutes() - m)
  return d.toISOString()
}

function secondsAgo(s: number): string {
  const d = new Date()
  d.setSeconds(d.getSeconds() - s)
  return d.toISOString()
}

// ---- Mock Investigations ----

export const MOCK_INVESTIGATIONS: AIInvestigation[] = [
  // Investigation for INC-1301 (Payment processing timeout)
  {
    id: "inv-001",
    incidentId: "INC-1301",
    status: "completed",
    startedAt: minutesAgo(8),
    completedAt: minutesAgo(7),
    durationSeconds: 34,
    confidenceScore: 92,
    summary:
      "Payment processing timeouts are caused by connection pool saturation on payment-service pods, triggered by degraded Stripe API performance in us-east-1. The payment-service HikariCP connection pool (max 200) is fully exhausted due to Stripe response times exceeding 8s (normal: <200ms). This causes cascading 504 errors on the API gateway /checkout endpoint.",
    rootCause:
      "Stripe API degraded performance in us-east-1 region causing connection hold times to exceed pool timeout thresholds. HikariCP pool maxed at 200 connections with avg hold time of 8.4s vs normal 180ms. Connection pool exhaustion leads to request queuing and eventual 504 Gateway Timeout responses.",
    affectedServices: [
      "payment-service",
      "api-gateway",
      "notification-service",
    ],
    remediationSteps: [
      {
        id: "rem-001-1",
        order: 1,
        description:
          "Scale payment-service to 8 replicas to increase total connection pool capacity",
        command:
          "kubectl scale deployment payment-service --replicas=8 -n commerce",
        riskLevel: "low",
        approval: "pending",
        estimatedImpact:
          "Increases total pool capacity from 200 to 800 connections",
      },
      {
        id: "rem-001-2",
        order: 2,
        description:
          "Increase HikariCP connection pool size from 200 to 500 and set connection timeout to 10s",
        command:
          'kubectl set env deployment/payment-service HIKARI_MAX_POOL_SIZE=500 HIKARI_CONNECTION_TIMEOUT=10000 -n commerce',
        riskLevel: "medium",
        approval: "pending",
        estimatedImpact:
          "Allows more concurrent connections but increases DB load",
      },
      {
        id: "rem-001-3",
        order: 3,
        description:
          "Enable circuit breaker on Stripe API calls with 5s timeout and 50% failure threshold",
        command:
          'kubectl set env deployment/payment-service STRIPE_CIRCUIT_BREAKER_ENABLED=true STRIPE_TIMEOUT_MS=5000 STRIPE_FAILURE_THRESHOLD=50 -n commerce',
        riskLevel: "medium",
        approval: "pending",
        estimatedImpact:
          "Fast-fails when Stripe is degraded, prevents pool exhaustion",
      },
      {
        id: "rem-001-4",
        order: 4,
        description:
          "Switch Stripe API region from us-east-1 to us-west-2 as failover",
        command:
          "kubectl set env deployment/payment-service STRIPE_API_REGION=us-west-2 -n commerce",
        riskLevel: "high",
        approval: "pending",
        estimatedImpact:
          "May resolve latency if us-west-2 is healthy; risk of payment routing issues",
      },
    ],
    toolCalls: [
      {
        id: "tc-001-1",
        toolName: "query_logs",
        description: "Querying payment-service logs for error patterns",
        status: "succeeded",
        durationMs: 2340,
        input:
          'service: payment-service | level: ERROR | last 30m | fields: message, trace_id, duration_ms',
        output:
          "Found 1,247 error entries. Top pattern: java.sql.SQLException: HikariPool-1 - Connection is not available (98.2%). Avg duration: 8420ms.",
      },
      {
        id: "tc-001-2",
        toolName: "query_metrics",
        description:
          "Fetching connection pool and latency metrics from Prometheus",
        status: "succeeded",
        durationMs: 1890,
        input:
          "hikaricp_connections_active{service='payment-service'}, http_server_duration_seconds{service='payment-service', route='/api/v2/payments'}",
        output:
          "Active connections: 200/200 (100% utilization). p99 latency: 8.42s, p50: 3.1s. Error rate: 34.2%. Started degrading at 14:37 UTC.",
      },
      {
        id: "tc-001-3",
        toolName: "query_traces",
        description:
          "Analyzing distributed traces for payment flow bottleneck",
        status: "succeeded",
        durationMs: 3120,
        input:
          "service: payment-service | operation: processPayment | status: ERROR | last 30m | limit: 50",
        output:
          "50 traces analyzed. Bottleneck: external call to api.stripe.com (span avg: 7.8s, normal: 180ms). Upstream api-gateway /checkout calls timing out at 5s gateway timeout.",
      },
      {
        id: "tc-001-4",
        toolName: "check_external_status",
        description: "Checking Stripe API status page",
        status: "succeeded",
        durationMs: 890,
        input: "https://status.stripe.com/api/v2/status.json",
        output:
          "Stripe status: Degraded Performance. Affected: API requests in us-east-1. Started: 14:30 UTC. ETA: Investigating.",
      },
      {
        id: "tc-001-5",
        toolName: "query_kubernetes",
        description: "Checking pod health and resource utilization",
        status: "succeeded",
        durationMs: 1450,
        input:
          "kubectl get pods -n commerce -l app=payment-service -o wide && kubectl top pods -n commerce -l app=payment-service",
        output:
          "4/4 pods Running. CPU: 45-62% (normal). Memory: 1.2-1.4GB/2GB. No OOMKills. No restarts in last 1h. All pods show connection pool at 100%.",
      },
      {
        id: "tc-001-6",
        toolName: "query_runbooks",
        description: "Searching runbooks for payment timeout procedures",
        status: "succeeded",
        durationMs: 670,
        input: "payment timeout connection pool exhaustion stripe degraded",
        output:
          "Found runbook: RB-PAY-003 'Payment Gateway Degradation'. Steps: 1) Confirm external provider status 2) Enable circuit breaker 3) Scale pods 4) Failover region if >30min.",
      },
    ],
    tokenUsage: {
      input: 42350,
      output: 4890,
      cached: 15200,
      estimatedCost: 0.18,
    },
    messages: [
      {
        id: "msg-001-1",
        role: "user",
        content:
          "Investigate incident INC-1301: Payment processing timeout. Payment gateway returning 504 errors for 30%+ of transactions.",
        timestamp: minutesAgo(8),
      },
      {
        id: "msg-001-2",
        role: "assistant",
        content:
          "Starting investigation of payment processing timeout. I'll analyze logs, metrics, traces, and external dependencies to identify the root cause.",
        timestamp: minutesAgo(8),
      },
      {
        id: "msg-001-3",
        role: "tool",
        content: "Querying payment-service error logs from the last 30 minutes...",
        timestamp: minutesAgo(8),
        toolCall: {
          id: "tc-001-1",
          toolName: "query_logs",
          description: "Querying payment-service logs for error patterns",
          status: "succeeded",
          durationMs: 2340,
          output:
            "Found 1,247 error entries. Top pattern: java.sql.SQLException: HikariPool-1 - Connection is not available (98.2%). Avg duration: 8420ms.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-001-4",
        role: "tool",
        content:
          "Fetching connection pool and latency metrics from Prometheus...",
        timestamp: minutesAgo(7),
        toolCall: {
          id: "tc-001-2",
          toolName: "query_metrics",
          description:
            "Fetching connection pool and latency metrics from Prometheus",
          status: "succeeded",
          durationMs: 1890,
          output:
            "Active connections: 200/200 (100% utilization). p99 latency: 8.42s, p50: 3.1s. Error rate: 34.2%.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-001-5",
        role: "assistant",
        content:
          "Connection pool is fully saturated (200/200). The p99 latency of 8.42s suggests an external dependency issue. Let me trace the specific bottleneck.",
        timestamp: minutesAgo(7),
      },
      {
        id: "msg-001-6",
        role: "tool",
        content: "Analyzing distributed traces for payment flow...",
        timestamp: minutesAgo(7),
        toolCall: {
          id: "tc-001-3",
          toolName: "query_traces",
          description:
            "Analyzing distributed traces for payment flow bottleneck",
          status: "succeeded",
          durationMs: 3120,
          output:
            "Bottleneck: external call to api.stripe.com (span avg: 7.8s, normal: 180ms). Upstream api-gateway /checkout calls timing out.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-001-7",
        role: "tool",
        content: "Checking Stripe API status page...",
        timestamp: minutesAgo(7),
        toolCall: {
          id: "tc-001-4",
          toolName: "check_external_status",
          description: "Checking Stripe API status page",
          status: "succeeded",
          durationMs: 890,
          output:
            "Stripe status: Degraded Performance in us-east-1. Started: 14:30 UTC.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-001-8",
        role: "assistant",
        content:
          "Root cause identified: Stripe API is experiencing degraded performance in us-east-1, causing response times to spike from 180ms to 7.8s. This exhausts the HikariCP connection pool (200 max), leading to cascading 504 errors.\n\nI'll check pod health and search for relevant runbooks to propose remediation steps.",
        timestamp: minutesAgo(7),
      },
      {
        id: "msg-001-9",
        role: "tool",
        content: "Checking Kubernetes pod status and resources...",
        timestamp: minutesAgo(7),
        toolCall: {
          id: "tc-001-5",
          toolName: "query_kubernetes",
          description: "Checking pod health and resource utilization",
          status: "succeeded",
          durationMs: 1450,
          output:
            "4/4 pods Running. CPU: 45-62%. Memory: 1.2-1.4GB/2GB. All pools at 100%.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-001-10",
        role: "tool",
        content: "Searching runbooks for payment timeout remediation...",
        timestamp: minutesAgo(7),
        toolCall: {
          id: "tc-001-6",
          toolName: "query_runbooks",
          description: "Searching runbooks for payment timeout procedures",
          status: "succeeded",
          durationMs: 670,
          output:
            "Found runbook: RB-PAY-003 'Payment Gateway Degradation'.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-001-11",
        role: "assistant",
        content:
          "Investigation complete. Root cause: Stripe API degraded performance in us-east-1 causing HikariCP connection pool exhaustion.\n\n**Confidence: 92%**\n\nI've prepared 4 remediation steps ordered by risk level, aligned with runbook RB-PAY-003. The immediate priority is scaling pods and enabling the circuit breaker to stop the cascading failure.",
        timestamp: minutesAgo(7),
      },
    ],
  },

  // Investigation for INC-1299 (Database connection pool exhausted)
  {
    id: "inv-002",
    incidentId: "INC-1299",
    status: "completed",
    startedAt: minutesAgo(45),
    completedAt: minutesAgo(44),
    durationSeconds: 28,
    confidenceScore: 88,
    summary:
      "Aurora PostgreSQL primary instance connection limit (500) exhausted by a combination of normal traffic and a runaway batch job in user-service. The batch job opened 120+ long-running connections for a user data migration that was not using connection pooling correctly, leaving insufficient connections for auth-service and user-service regular operations.",
    rootCause:
      "user-service batch job (UserDataMigrationJob) spawning unbounded connections without using the shared PgBouncer pool. Each batch worker opens a direct connection to Aurora, bypassing connection limits. Combined with normal traffic (~350 connections), total exceeded the 500 max_connections limit.",
    affectedServices: ["auth-service", "user-service", "api-gateway"],
    remediationSteps: [
      {
        id: "rem-002-1",
        order: 1,
        description:
          "Kill idle connections from the batch job that have been open for more than 10 minutes",
        command:
          "kubectl exec -n data aurora-primary-01 -- psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name = 'UserDataMigrationJob' AND state = 'idle' AND query_start < now() - interval '10 minutes';\"",
        riskLevel: "low",
        approval: "pending",
        estimatedImpact:
          "Frees ~80 connections immediately, restoring service availability",
      },
      {
        id: "rem-002-2",
        order: 2,
        description:
          "Suspend the UserDataMigrationJob CronJob until connection pooling is fixed",
        command:
          "kubectl patch cronjob user-data-migration -n data -p '{\"spec\":{\"suspend\":true}}'",
        riskLevel: "low",
        approval: "pending",
        estimatedImpact:
          "Prevents recurrence of the connection flood",
      },
      {
        id: "rem-002-3",
        order: 3,
        description:
          "Deploy PgBouncer sidecar for connection pooling on all database-connected services",
        command:
          "kubectl apply -f infrastructure/pgbouncer/pgbouncer-sidecar.yaml -n commerce && kubectl apply -f infrastructure/pgbouncer/pgbouncer-sidecar.yaml -n data",
        riskLevel: "medium",
        approval: "pending",
        estimatedImpact:
          "Connection multiplexing reduces direct DB connections by ~70%",
      },
      {
        id: "rem-002-4",
        order: 4,
        description:
          "Increase Aurora max_connections from 500 to 800 (requires parameter group update and reboot)",
        command:
          "aws rds modify-db-parameter-group --db-parameter-group-name aurora-pg16-prod --parameters \"ParameterName=max_connections,ParameterValue=800,ApplyMethod=pending-reboot\"",
        riskLevel: "high",
        approval: "pending",
        estimatedImpact:
          "Increases headroom but requires rolling reboot during maintenance window",
      },
    ],
    toolCalls: [
      {
        id: "tc-002-1",
        toolName: "query_metrics",
        description: "Fetching RDS connection metrics from Prometheus",
        status: "succeeded",
        durationMs: 1680,
        input:
          "rds_connections_active{instance='aurora-primary-01'}, rds_connections_by_app{instance='aurora-primary-01'}",
        output:
          "Total: 500/500. Breakdown: auth-service: 180, user-service: 150, UserDataMigrationJob: 125, api-gateway: 30, other: 15.",
      },
      {
        id: "tc-002-2",
        toolName: "query_logs",
        description:
          "Querying auth-service and user-service logs for connection errors",
        status: "succeeded",
        durationMs: 2100,
        input:
          'service: auth-service OR user-service | level: ERROR | message: "connection" | last 2h',
        output:
          "auth-service: 892 errors 'FATAL: too many connections for role \"auth_app\"'. user-service: 456 errors, same pattern. First occurrence: 2h ago.",
      },
      {
        id: "tc-002-3",
        toolName: "query_database",
        description: "Checking pg_stat_activity for long-running connections",
        status: "succeeded",
        durationMs: 1240,
        input:
          "SELECT application_name, state, count(*), avg(extract(epoch from now() - query_start)) as avg_duration FROM pg_stat_activity GROUP BY application_name, state ORDER BY count DESC",
        output:
          "UserDataMigrationJob | idle: 82 (avg 845s), active: 43 (avg 120s). auth-service | active: 145, idle: 35. user-service | active: 112, idle: 38.",
      },
      {
        id: "tc-002-4",
        toolName: "query_kubernetes",
        description: "Checking batch job status and configuration",
        status: "succeeded",
        durationMs: 980,
        input:
          "kubectl describe cronjob user-data-migration -n data && kubectl get jobs -n data --sort-by=.metadata.creationTimestamp | tail -5",
        output:
          "CronJob: user-data-migration, Schedule: '0 */4 * * *', Active: 1. Last job started 2h12m ago. parallelism: 10, No connection pool config found.",
      },
      {
        id: "tc-002-5",
        toolName: "query_runbooks",
        description:
          "Searching runbooks for database connection exhaustion procedures",
        status: "succeeded",
        durationMs: 540,
        input: "database connection pool exhausted aurora postgresql",
        output:
          "Found runbook: RB-DB-001 'Database Connection Exhaustion'. Steps: 1) Identify top consumers via pg_stat_activity 2) Kill idle connections 3) Deploy PgBouncer 4) Increase max_connections.",
      },
    ],
    tokenUsage: {
      input: 38720,
      output: 5210,
      cached: 14800,
      estimatedCost: 0.16,
    },
    messages: [
      {
        id: "msg-002-1",
        role: "user",
        content:
          "Investigate incident INC-1299: Database connection pool exhausted. Aurora PostgreSQL primary at 500/500 connections.",
        timestamp: minutesAgo(45),
      },
      {
        id: "msg-002-2",
        role: "assistant",
        content:
          "Investigating the connection pool exhaustion. I'll query connection metrics, application logs, and the database directly to identify which applications are consuming connections.",
        timestamp: minutesAgo(45),
      },
      {
        id: "msg-002-3",
        role: "tool",
        content: "Fetching RDS connection metrics from Prometheus...",
        timestamp: minutesAgo(45),
        toolCall: {
          id: "tc-002-1",
          toolName: "query_metrics",
          description: "Fetching RDS connection metrics from Prometheus",
          status: "succeeded",
          durationMs: 1680,
          output:
            "Total: 500/500. UserDataMigrationJob: 125 connections. auth-service: 180, user-service: 150.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-002-4",
        role: "assistant",
        content:
          "UserDataMigrationJob is holding 125 connections -- that's unusual for a batch job. Let me check the logs and database activity.",
        timestamp: minutesAgo(45),
      },
      {
        id: "msg-002-5",
        role: "tool",
        content: "Querying service logs for connection errors...",
        timestamp: minutesAgo(45),
        toolCall: {
          id: "tc-002-2",
          toolName: "query_logs",
          description:
            "Querying auth-service and user-service logs for connection errors",
          status: "succeeded",
          durationMs: 2100,
          output:
            "892 errors on auth-service, 456 on user-service. 'FATAL: too many connections'.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-002-6",
        role: "tool",
        content: "Checking pg_stat_activity for connection breakdown...",
        timestamp: minutesAgo(44),
        toolCall: {
          id: "tc-002-3",
          toolName: "query_database",
          description:
            "Checking pg_stat_activity for long-running connections",
          status: "succeeded",
          durationMs: 1240,
          output:
            "UserDataMigrationJob: 82 idle (avg 845s hold time), 43 active. Not using connection pooling.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-002-7",
        role: "assistant",
        content:
          "Found it. The UserDataMigrationJob has 82 idle connections held for an average of 14 minutes each. It's bypassing PgBouncer and opening direct connections to Aurora. Let me verify the job configuration.",
        timestamp: minutesAgo(44),
      },
      {
        id: "msg-002-8",
        role: "tool",
        content: "Checking batch job configuration...",
        timestamp: minutesAgo(44),
        toolCall: {
          id: "tc-002-4",
          toolName: "query_kubernetes",
          description: "Checking batch job status and configuration",
          status: "succeeded",
          durationMs: 980,
          output:
            "CronJob runs every 4h with parallelism=10. No connection pool config. Last run: 2h12m ago.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-002-9",
        role: "tool",
        content: "Searching runbooks for remediation procedures...",
        timestamp: minutesAgo(44),
        toolCall: {
          id: "tc-002-5",
          toolName: "query_runbooks",
          description:
            "Searching runbooks for database connection exhaustion procedures",
          status: "succeeded",
          durationMs: 540,
          output: "Found runbook: RB-DB-001 'Database Connection Exhaustion'.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-002-10",
        role: "assistant",
        content:
          "Investigation complete. Root cause: UserDataMigrationJob CronJob (runs every 4h, parallelism=10) opens direct connections to Aurora without pooling, holding 125 connections (82 idle for 14min+). Combined with normal traffic of ~350 connections, this exceeds the 500 limit.\n\n**Confidence: 88%**\n\nRemediation plan follows runbook RB-DB-001: immediate connection cleanup, suspend the job, deploy PgBouncer, then increase max_connections in the next maintenance window.",
        timestamp: minutesAgo(44),
      },
    ],
  },

  // Investigation for INC-1295 (Memory leak in auth-service)
  {
    id: "inv-003",
    incidentId: "INC-1295",
    status: "completed",
    startedAt: minutesAgo(120),
    completedAt: minutesAgo(119),
    durationSeconds: 45,
    confidenceScore: 95,
    summary:
      "auth-service pods are experiencing a memory leak due to a disabled cache eviction policy in the token cache module, introduced in version 1.8.3. The JVM heap grows linearly from 512MB to 2GB over 4-6 hours as JWT token entries accumulate without eviction, eventually triggering OOMKill.",
    rootCause:
      "In auth-service v1.8.3 (deployed 3 days ago), commit abc123f disabled the Caffeine cache eviction policy for the token cache as part of a 'performance optimization'. The cache.maximumSize() and cache.expireAfterWrite() settings were removed, causing unbounded growth. Each cached JWT entry is ~2KB, and with ~500 authentications/sec, the cache grows at ~1MB/sec.",
    affectedServices: ["auth-service"],
    remediationSteps: [
      {
        id: "rem-003-1",
        order: 1,
        description:
          "Rolling restart auth-service pods to clear accumulated cache and restore memory",
        command:
          "kubectl rollout restart deployment/auth-service -n auth",
        riskLevel: "low",
        approval: "pending",
        estimatedImpact:
          "Temporary fix -- clears memory but leak will recur in 4-6 hours",
      },
      {
        id: "rem-003-2",
        order: 2,
        description:
          "Deploy hotfix to re-enable token cache eviction policy (PR #482)",
        command:
          "kubectl set image deployment/auth-service auth-service=registry.internal/auth-service:1.8.4-hotfix -n auth",
        riskLevel: "medium",
        approval: "pending",
        estimatedImpact:
          "Permanent fix -- restores cache eviction, memory stable at ~600MB",
      },
      {
        id: "rem-003-3",
        order: 3,
        description:
          "Add JVM heap monitoring alert at 70% threshold to catch memory issues earlier",
        command:
          'kubectl apply -f - <<EOF\napiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nmetadata:\n  name: auth-service-heap-alert\n  namespace: auth\nspec:\n  groups:\n  - name: auth-service-memory\n    rules:\n    - alert: AuthServiceHeapHigh\n      expr: jvm_memory_used_bytes{area="heap",service="auth-service"} / jvm_memory_max_bytes{area="heap",service="auth-service"} > 0.7\n      for: 5m\nEOF',
        riskLevel: "low",
        approval: "pending",
        estimatedImpact:
          "Earlier detection of future memory issues (alerts at 70% vs current 90%)",
      },
    ],
    toolCalls: [
      {
        id: "tc-003-1",
        toolName: "query_metrics",
        description: "Fetching JVM heap and container memory metrics",
        status: "succeeded",
        durationMs: 1920,
        input:
          "jvm_memory_used_bytes{service='auth-service',area='heap'}, container_memory_working_set_bytes{pod=~'auth-service.*'}",
        output:
          "Heap: linear growth from 512MB to 1.8GB over 5h. Container RSS: 1.9GB/2GB limit. Growth rate: ~1MB/sec. No GC reclamation of old gen.",
      },
      {
        id: "tc-003-2",
        toolName: "query_logs",
        description: "Querying for OOMKill events and GC logs",
        status: "succeeded",
        durationMs: 1650,
        input:
          'service: auth-service | (message: "OOMKilled" OR message: "GC overhead" OR message: "heap space") | last 48h',
        output:
          "Found 8 OOMKill events in last 48h. Interval: every 4-6h. Last: 3h ago. GC logs show Full GC every 30min after 3h uptime with decreasing freed memory.",
      },
      {
        id: "tc-003-3",
        toolName: "query_kubernetes",
        description: "Checking deployment history and recent changes",
        status: "succeeded",
        durationMs: 1100,
        input:
          "kubectl rollout history deployment/auth-service -n auth && kubectl describe deployment auth-service -n auth | grep Image",
        output:
          "Revision 1: v1.8.2 (stable). Revision 2: v1.8.3 (3 days ago). Current: v1.8.3. Image: registry.internal/auth-service:1.8.3.",
      },
      {
        id: "tc-003-4",
        toolName: "query_git",
        description: "Analyzing v1.8.3 diff for memory-related changes",
        status: "succeeded",
        durationMs: 2340,
        input:
          "git log v1.8.2..v1.8.3 --oneline -- '**/cache/**' '**/token/**'",
        output:
          "Commit abc123f: 'perf: remove cache size limits for faster token lookups'. Changed TokenCacheConfig.java: removed cache.maximumSize(10000) and cache.expireAfterWrite(Duration.ofMinutes(15)).",
      },
      {
        id: "tc-003-5",
        toolName: "analyze_heap_dump",
        description: "Analyzing latest heap dump from OOMKilled pod",
        status: "succeeded",
        durationMs: 4200,
        input: "heap-dump-auth-service-7f4b8c-20260410-1130.hprof",
        output:
          "Largest retained: ConcurrentHashMap (TokenCache) at 1.4GB (72% of heap). 687,000 entries. Key: JWT jti claim. Value: TokenCacheEntry (~2KB each). No eviction metadata present.",
      },
      {
        id: "tc-003-6",
        toolName: "query_runbooks",
        description: "Searching for memory leak remediation procedures",
        status: "succeeded",
        durationMs: 480,
        input: "memory leak auth-service OOMKill cache",
        output:
          "Found runbook: RB-AUTH-002 'Auth Service Memory Issues'. Steps: 1) Rolling restart 2) Check cache config 3) Deploy fix 4) Add heap alerts.",
      },
    ],
    tokenUsage: {
      input: 45100,
      output: 5620,
      cached: 16400,
      estimatedCost: 0.21,
    },
    messages: [
      {
        id: "msg-003-1",
        role: "user",
        content:
          "Investigate incident INC-1295: Memory leak in auth-service. Pods OOMKilled every 4-6 hours.",
        timestamp: minutesAgo(120),
      },
      {
        id: "msg-003-2",
        role: "assistant",
        content:
          "Investigating the memory leak. I'll analyze heap metrics, OOMKill events, recent deployments, and code changes to pinpoint the leak.",
        timestamp: minutesAgo(120),
      },
      {
        id: "msg-003-3",
        role: "tool",
        content: "Fetching JVM heap and container memory metrics...",
        timestamp: minutesAgo(120),
        toolCall: {
          id: "tc-003-1",
          toolName: "query_metrics",
          description: "Fetching JVM heap and container memory metrics",
          status: "succeeded",
          durationMs: 1920,
          output:
            "Heap grows linearly from 512MB to 1.8GB over 5h. No GC reclamation.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-003-4",
        role: "tool",
        content: "Querying for OOMKill events and GC logs...",
        timestamp: minutesAgo(120),
        toolCall: {
          id: "tc-003-2",
          toolName: "query_logs",
          description: "Querying for OOMKill events and GC logs",
          status: "succeeded",
          durationMs: 1650,
          output: "8 OOMKill events in 48h. Every 4-6h.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-003-5",
        role: "assistant",
        content:
          "Clear linear memory growth pattern -- this is a classic unbounded cache or leak. Let me check what changed recently.",
        timestamp: minutesAgo(120),
      },
      {
        id: "msg-003-6",
        role: "tool",
        content: "Checking deployment history...",
        timestamp: minutesAgo(119),
        toolCall: {
          id: "tc-003-3",
          toolName: "query_kubernetes",
          description: "Checking deployment history and recent changes",
          status: "succeeded",
          durationMs: 1100,
          output: "v1.8.3 deployed 3 days ago. Previous: v1.8.2 (stable).",
        },
        isCollapsible: true,
      },
      {
        id: "msg-003-7",
        role: "tool",
        content: "Analyzing v1.8.3 code changes for memory-related modifications...",
        timestamp: minutesAgo(119),
        toolCall: {
          id: "tc-003-4",
          toolName: "query_git",
          description: "Analyzing v1.8.3 diff for memory-related changes",
          status: "succeeded",
          durationMs: 2340,
          output:
            "Commit abc123f removed cache.maximumSize(10000) and cache.expireAfterWrite(15min) from TokenCacheConfig.java.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-003-8",
        role: "assistant",
        content:
          "Found it. Commit abc123f in v1.8.3 removed cache size limits and TTL from the token cache. Let me verify with a heap dump analysis.",
        timestamp: minutesAgo(119),
      },
      {
        id: "msg-003-9",
        role: "tool",
        content: "Analyzing heap dump from latest OOMKilled pod...",
        timestamp: minutesAgo(119),
        toolCall: {
          id: "tc-003-5",
          toolName: "analyze_heap_dump",
          description: "Analyzing latest heap dump from OOMKilled pod",
          status: "succeeded",
          durationMs: 4200,
          output:
            "TokenCache ConcurrentHashMap: 1.4GB, 687K entries, no eviction.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-003-10",
        role: "tool",
        content: "Searching runbooks for remediation procedures...",
        timestamp: minutesAgo(119),
        toolCall: {
          id: "tc-003-6",
          toolName: "query_runbooks",
          description: "Searching for memory leak remediation procedures",
          status: "succeeded",
          durationMs: 480,
          output:
            "Found runbook: RB-AUTH-002 'Auth Service Memory Issues'.",
        },
        isCollapsible: true,
      },
      {
        id: "msg-003-11",
        role: "assistant",
        content:
          "Investigation complete. Root cause confirmed with high confidence: commit abc123f in v1.8.3 disabled Caffeine cache eviction for the token cache. The heap dump shows 687K entries (1.4GB) in the TokenCache with no eviction policy. At ~500 auth/sec and ~2KB per entry, the cache fills 2GB in about 4-6 hours, matching the OOMKill pattern exactly.\n\n**Confidence: 95%**\n\nFix PR #482 has already been created by Lisa Wang. Recommended: rolling restart now for immediate relief, then deploy the hotfix.",
        timestamp: minutesAgo(119),
      },
    ],
  },
]

// ---- Lookup helpers ----

export function getInvestigationByIncidentId(
  incidentId: string
): AIInvestigation | undefined {
  return MOCK_INVESTIGATIONS.find((inv) => inv.incidentId === incidentId)
}

export function getInvestigationById(
  id: string
): AIInvestigation | undefined {
  return MOCK_INVESTIGATIONS.find((inv) => inv.id === id)
}
