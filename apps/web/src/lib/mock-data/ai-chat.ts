// ---- Types ----

export type ChatRole = "user" | "assistant"
export type ToolCallStatus = "running" | "success" | "failed"

export interface ToolCall {
  id: string
  toolName: string
  status: ToolCallStatus
  durationMs: number
  result?: string
}

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  timestamp: string
  toolCalls?: ToolCall[]
}

// ---- Mock conversation ----

export const mockMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "What's the current system status?",
    timestamp: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
  },
  {
    id: "msg-2",
    role: "assistant",
    content:
      "I've checked across your infrastructure. Here's the current status:\n\n**Critical:**\n- `notification-service` is returning 5xx errors (started ~12 min ago)\n- SLO for `payment-gateway` latency is breaching (p99 > 800ms)\n\n**Warnings:**\n- `auth-service` error rate trending up (0.8% -> 1.2%)\n- Cost anomaly detected in `us-east-1` compute spend (+23% vs forecast)\n- `user-service` SLO at risk (99.1% vs 99.5% target)\n\n**Healthy:**\n- `api-gateway` — 99.99% uptime\n- `order-service` — all SLOs met\n- `search-service` — nominal\n- `inventory-service` — nominal",
    timestamp: new Date(Date.now() - 7 * 60 * 1000).toISOString(),
    toolCalls: [
      {
        id: "tc-1",
        toolName: "query_metrics",
        status: "success",
        durationMs: 1240,
        result: JSON.stringify(
          {
            services_checked: 8,
            critical: 2,
            warning: 3,
            healthy: 4,
            time_range: "last_15m",
          },
          null,
          2
        ),
      },
      {
        id: "tc-2",
        toolName: "query_logs",
        status: "success",
        durationMs: 890,
        result: JSON.stringify(
          {
            total_errors: 147,
            top_service: "notification-service",
            error_pattern: "ConnectionTimeoutException",
            first_seen: "12m ago",
          },
          null,
          2
        ),
      },
    ],
  },
  {
    id: "msg-3",
    role: "user",
    content: "Why is notification-service down?",
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
  {
    id: "msg-4",
    role: "assistant",
    content:
      "Based on my investigation, the `notification-service` failures are caused by a **downstream dependency timeout** to the email provider (SendGrid).\n\n**Root Cause:**\nSendGrid's `api.sendgrid.com` endpoint is responding with elevated latency (avg 12s, normally <200ms). This is causing connection pool exhaustion in the notification-service.\n\n**Evidence:**\n- 147 `ConnectionTimeoutException` errors in the last 12 minutes\n- All errors originate from the `EmailNotificationHandler` class\n- SendGrid status page confirms degraded API performance\n- No recent deployments to notification-service (last deploy: 3 days ago)\n\n**Recommended Actions:**\n1. Enable circuit breaker for SendGrid calls (estimated: low risk)\n2. Switch to fallback SMS provider for critical notifications\n3. Monitor SendGrid status page for resolution",
    timestamp: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
    toolCalls: [
      {
        id: "tc-3",
        toolName: "query_logs",
        status: "success",
        durationMs: 1560,
        result: JSON.stringify(
          {
            service: "notification-service",
            error_count: 147,
            error_class: "ConnectionTimeoutException",
            stack_trace_sample:
              "at EmailNotificationHandler.send(EmailNotificationHandler.java:142)",
            affected_endpoint: "api.sendgrid.com",
          },
          null,
          2
        ),
      },
      {
        id: "tc-4",
        toolName: "query_deployments",
        status: "success",
        durationMs: 420,
        result: JSON.stringify(
          {
            service: "notification-service",
            last_deploy: "3d ago",
            last_deploy_sha: "a1b2c3d",
            deployer: "ci/cd",
            status: "stable",
          },
          null,
          2
        ),
      },
      {
        id: "tc-5",
        toolName: "check_external_status",
        status: "success",
        durationMs: 2100,
        result: JSON.stringify(
          {
            provider: "SendGrid",
            status: "degraded",
            component: "API v3",
            incident_url: "https://status.sendgrid.com/incidents/...",
            started_at: "15m ago",
          },
          null,
          2
        ),
      },
    ],
  },
]

// ---- System summary mock data ----

export interface SystemSummaryItem {
  level: "critical" | "warning" | "healthy"
  count: number
  description: string
}

export const mockSystemSummary: SystemSummaryItem[] = [
  {
    level: "critical",
    count: 2,
    description: "2 critical incidents, 1 breaching SLO",
  },
  {
    level: "warning",
    count: 3,
    description: "3 at-risk SLOs, 1 cost anomaly",
  },
  {
    level: "healthy",
    count: 4,
    description: "4 services healthy",
  },
]
