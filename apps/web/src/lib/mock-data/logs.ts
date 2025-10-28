export type LogLevel = "TRACE" | "DEBUG" | "INFO" | "WARN" | "ERROR" | "FATAL"

export interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  service: string
  message: string
  traceId?: string
  spanId?: string
  attributes?: Record<string, string>
  security?: boolean
  securityCategory?: "auth_failure" | "privilege_escalation" | "network_anomaly" | "secret_exposure" | "cve_alert"
}

const SERVICES = [
  "api-gateway",
  "auth-service",
  "user-service",
  "payment-service",
  "notification-service",
  "deployment-controller",
  "config-service",
  "audit-service",
] as const

export type ServiceName = (typeof SERVICES)[number]

export const SERVICE_LIST: string[] = [...SERVICES]

function generateId(index: number): string {
  return `log-${String(index).padStart(5, "0")}`
}

function generateTraceId(): string {
  const chars = "0123456789abcdef"
  let id = ""
  for (let i = 0; i < 32; i++) {
    id += chars[Math.floor(Math.random() * 16)]
  }
  return id
}

function generateSpanId(): string {
  const chars = "0123456789abcdef"
  let id = ""
  for (let i = 0; i < 16; i++) {
    id += chars[Math.floor(Math.random() * 16)]
  }
  return id
}

// Spread timestamps across the last 24 hours
function generateTimestamp(index: number, total: number): string {
  const now = new Date()
  const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const timeSpan = now.getTime() - twentyFourHoursAgo.getTime()
  const offset = (index / total) * timeSpan
  return new Date(twentyFourHoursAgo.getTime() + offset).toISOString()
}

interface LogTemplate {
  level: LogLevel
  service: ServiceName
  message: string
  security?: boolean
  securityCategory?: LogEntry["securityCategory"]
  attributes?: Record<string, string>
  hasTrace?: boolean
}

const LOG_TEMPLATES: LogTemplate[] = [
  // api-gateway - HTTP requests
  { level: "INFO", service: "api-gateway", message: "GET /api/v1/users 200 12ms", hasTrace: true, attributes: { method: "GET", path: "/api/v1/users", status: "200", duration: "12ms", client_ip: "10.0.1.45" } },
  { level: "INFO", service: "api-gateway", message: "POST /api/v1/auth/login 200 89ms", hasTrace: true, attributes: { method: "POST", path: "/api/v1/auth/login", status: "200", duration: "89ms", client_ip: "10.0.2.12" } },
  { level: "INFO", service: "api-gateway", message: "GET /api/v1/payments/history 200 234ms", hasTrace: true, attributes: { method: "GET", path: "/api/v1/payments/history", status: "200", duration: "234ms", client_ip: "10.0.1.78" } },
  { level: "WARN", service: "api-gateway", message: "Rate limit approaching for client 10.0.3.22 (980/1000 requests)", attributes: { client_ip: "10.0.3.22", rate_limit: "1000", current: "980" } },
  { level: "ERROR", service: "api-gateway", message: "POST /api/v1/payments/charge 502 Bad Gateway - upstream timeout after 30s", hasTrace: true, attributes: { method: "POST", path: "/api/v1/payments/charge", status: "502", error: "upstream_timeout", upstream: "payment-service:8080" } },
  { level: "INFO", service: "api-gateway", message: "GET /api/v1/notifications 200 45ms", hasTrace: true, attributes: { method: "GET", path: "/api/v1/notifications", status: "200", duration: "45ms" } },
  { level: "INFO", service: "api-gateway", message: "PUT /api/v1/users/profile 200 67ms", hasTrace: true, attributes: { method: "PUT", path: "/api/v1/users/profile", status: "200", duration: "67ms" } },
  { level: "WARN", service: "api-gateway", message: "Slow upstream response from auth-service: 2847ms", hasTrace: true, attributes: { upstream: "auth-service:8081", latency: "2847ms", threshold: "1000ms" } },
  { level: "INFO", service: "api-gateway", message: "GET /healthz 200 1ms", attributes: { method: "GET", path: "/healthz", status: "200" } },
  { level: "DEBUG", service: "api-gateway", message: "TLS handshake completed: TLS 1.3, ECDHE-RSA-AES256-GCM-SHA384", attributes: { tls_version: "1.3", cipher: "ECDHE-RSA-AES256-GCM-SHA384" } },

  // auth-service
  { level: "INFO", service: "auth-service", message: "User login successful: user_id=usr_847291 email=john@example.com", hasTrace: true, attributes: { user_id: "usr_847291", email: "john@example.com", method: "password", mfa: "true" } },
  { level: "WARN", service: "auth-service", message: "Failed login attempt for user admin@company.com (3/5 attempts)", security: true, securityCategory: "auth_failure", attributes: { email: "admin@company.com", attempts: "3", max_attempts: "5", source_ip: "203.0.113.42" } },
  { level: "ERROR", service: "auth-service", message: "Failed login attempt for user admin@company.com - account locked after 5 failed attempts", security: true, securityCategory: "auth_failure", attributes: { email: "admin@company.com", attempts: "5", action: "account_locked", source_ip: "203.0.113.42" } },
  { level: "INFO", service: "auth-service", message: "JWT token issued for user usr_384712, expires in 3600s", hasTrace: true, attributes: { user_id: "usr_384712", token_type: "access", ttl: "3600s" } },
  { level: "INFO", service: "auth-service", message: "Token refresh successful for session sess_291847", hasTrace: true, attributes: { session_id: "sess_291847", new_ttl: "3600s" } },
  { level: "WARN", service: "auth-service", message: "Expired token presented by client 10.0.1.99 - token expired 47 minutes ago", attributes: { client_ip: "10.0.1.99", expired_since: "47m" } },
  { level: "ERROR", service: "auth-service", message: "OIDC provider connection failed: Keycloak unreachable at keycloak.internal:8443", attributes: { provider: "keycloak", endpoint: "keycloak.internal:8443", error: "connection_refused" } },
  { level: "FATAL", service: "auth-service", message: "Critical: JWT signing key rotation failed - unable to write to secrets store", security: true, securityCategory: "secret_exposure", attributes: { error: "secrets_store_write_failed", store: "aws-secrets-manager", region: "ap-northeast-2" } },
  { level: "WARN", service: "auth-service", message: "Privilege escalation attempt: user usr_100234 tried to access admin endpoint /admin/users", security: true, securityCategory: "privilege_escalation", hasTrace: true, attributes: { user_id: "usr_100234", endpoint: "/admin/users", role: "viewer", required_role: "admin" } },
  { level: "INFO", service: "auth-service", message: "OAuth2 client credentials validated for service payment-service", attributes: { client_id: "svc_payment", grant_type: "client_credentials" } },

  // user-service
  { level: "INFO", service: "user-service", message: "User profile updated: usr_384712 changed display_name", hasTrace: true, attributes: { user_id: "usr_384712", field: "display_name" } },
  { level: "INFO", service: "user-service", message: "Database query completed: SELECT * FROM users WHERE active=true (23ms, 1847 rows)", attributes: { query_type: "SELECT", table: "users", duration: "23ms", rows: "1847" } },
  { level: "WARN", service: "user-service", message: "Slow query detected: SELECT * FROM user_preferences JOIN notifications (1247ms)", attributes: { query_type: "SELECT", tables: "user_preferences,notifications", duration: "1247ms", threshold: "1000ms" } },
  { level: "ERROR", service: "user-service", message: "Database connection pool exhausted - 50/50 connections in use, 12 waiters", attributes: { pool_size: "50", active: "50", waiting: "12", database: "users-primary.rds.amazonaws.com" } },
  { level: "INFO", service: "user-service", message: "Cache hit for user profile usr_291847 (Redis, 0.3ms)", attributes: { user_id: "usr_291847", cache: "redis", latency: "0.3ms" } },
  { level: "DEBUG", service: "user-service", message: "Cache miss for user preferences usr_182947 - fetching from database", attributes: { user_id: "usr_182947", cache: "redis" } },
  { level: "INFO", service: "user-service", message: "Batch user sync completed: 342 users synced from LDAP", attributes: { source: "ldap", synced: "342", errors: "0" } },
  { level: "INFO", service: "user-service", message: "User registration: new account created usr_999012 email=jane@startup.io", hasTrace: true, attributes: { user_id: "usr_999012", email: "jane@startup.io", method: "email" } },

  // payment-service
  { level: "INFO", service: "payment-service", message: "Payment processed: txn_847291 amount=$129.99 currency=USD status=completed", hasTrace: true, attributes: { transaction_id: "txn_847291", amount: "129.99", currency: "USD", status: "completed", provider: "stripe" } },
  { level: "WARN", service: "payment-service", message: "Payment retry #2 for txn_384712 - provider returned temporary error", hasTrace: true, attributes: { transaction_id: "txn_384712", retry: "2", error: "provider_temporary_error" } },
  { level: "ERROR", service: "payment-service", message: "Payment failed: txn_192847 - card declined (insufficient_funds)", hasTrace: true, attributes: { transaction_id: "txn_192847", error: "card_declined", decline_code: "insufficient_funds" } },
  { level: "INFO", service: "payment-service", message: "Refund initiated: txn_738291 amount=$49.99 reason=customer_request", hasTrace: true, attributes: { transaction_id: "txn_738291", amount: "49.99", type: "refund", reason: "customer_request" } },
  { level: "INFO", service: "payment-service", message: "Webhook received from Stripe: invoice.payment_succeeded for cus_847291", attributes: { event: "invoice.payment_succeeded", customer: "cus_847291", provider: "stripe" } },
  { level: "WARN", service: "payment-service", message: "Webhook signature verification slow: 890ms (threshold 500ms)", attributes: { duration: "890ms", threshold: "500ms" } },
  { level: "ERROR", service: "payment-service", message: "Database deadlock detected during concurrent payment updates on txn_291847", attributes: { transaction_id: "txn_291847", error: "deadlock_detected", table: "transactions" } },
  { level: "DEBUG", service: "payment-service", message: "Idempotency key check: key_8472910 - no existing transaction found", attributes: { idempotency_key: "key_8472910" } },

  // notification-service
  { level: "INFO", service: "notification-service", message: "Email sent: template=welcome recipient=jane@startup.io provider=ses", hasTrace: true, attributes: { template: "welcome", recipient: "jane@startup.io", provider: "ses", message_id: "msg_847291" } },
  { level: "INFO", service: "notification-service", message: "Push notification delivered: device=ios_847291 type=payment_confirmation", attributes: { device_type: "ios", device_id: "ios_847291", type: "payment_confirmation" } },
  { level: "WARN", service: "notification-service", message: "Email delivery delayed: SES throttling - 14/sec (limit 14/sec)", attributes: { provider: "ses", rate: "14/sec", limit: "14/sec" } },
  { level: "ERROR", service: "notification-service", message: "SMS delivery failed: invalid phone number +1-555-000-0000 for user usr_291847", attributes: { user_id: "usr_291847", phone: "+1-555-000-0000", error: "invalid_number" } },
  { level: "INFO", service: "notification-service", message: "Notification preferences updated for usr_384712: email=on, push=off, sms=off", attributes: { user_id: "usr_384712", email: "on", push: "off", sms: "off" } },
  { level: "DEBUG", service: "notification-service", message: "Template rendered: payment_receipt (12ms), size=4.2KB", attributes: { template: "payment_receipt", render_time: "12ms", size: "4.2KB" } },

  // deployment-controller
  { level: "INFO", service: "deployment-controller", message: "Deployment started: app=user-service version=v2.14.3 strategy=rolling", hasTrace: true, attributes: { app: "user-service", version: "v2.14.3", strategy: "rolling", replicas: "5", namespace: "production" } },
  { level: "INFO", service: "deployment-controller", message: "Rolling update progress: user-service 3/5 replicas updated", attributes: { app: "user-service", updated: "3", total: "5" } },
  { level: "INFO", service: "deployment-controller", message: "Deployment completed: app=user-service version=v2.14.3 duration=4m32s", hasTrace: true, attributes: { app: "user-service", version: "v2.14.3", duration: "4m32s", status: "success" } },
  { level: "WARN", service: "deployment-controller", message: "Deployment rollback triggered: app=payment-service health check failed (3/3 probes)", attributes: { app: "payment-service", reason: "health_check_failed", probes_failed: "3" } },
  { level: "ERROR", service: "deployment-controller", message: "Deployment failed: app=api-gateway - image pull error: registry.internal/api-gateway:v3.0.0 not found", attributes: { app: "api-gateway", error: "image_pull_error", image: "registry.internal/api-gateway:v3.0.0" } },
  { level: "INFO", service: "deployment-controller", message: "ArgoCD sync completed: app=notification-service revision=abc1234", attributes: { app: "notification-service", revision: "abc1234", sync_status: "Synced", health_status: "Healthy" } },
  { level: "INFO", service: "deployment-controller", message: "Canary analysis passed: payment-service v2.8.0 error_rate=0.01% (threshold 1%)", attributes: { app: "payment-service", version: "v2.8.0", error_rate: "0.01%", threshold: "1%", verdict: "pass" } },

  // config-service
  { level: "INFO", service: "config-service", message: "Configuration updated: feature_flags.dark_mode=enabled (environment: production)", attributes: { key: "feature_flags.dark_mode", value: "enabled", environment: "production" } },
  { level: "INFO", service: "config-service", message: "Secret rotation completed: db-password-user-service rotated successfully", attributes: { secret: "db-password-user-service", rotation_status: "success" } },
  { level: "WARN", service: "config-service", message: "Configuration drift detected: auth-service has 3 unsynced environment variables", attributes: { service: "auth-service", drift_count: "3" } },
  { level: "DEBUG", service: "config-service", message: "External Secrets Operator sync: 47 secrets synced from AWS Secrets Manager", attributes: { synced: "47", provider: "aws-secrets-manager", duration: "1.2s" } },

  // audit-service
  { level: "INFO", service: "audit-service", message: "Audit log: user admin@company.com accessed /admin/billing from 10.0.1.5", attributes: { user: "admin@company.com", resource: "/admin/billing", source_ip: "10.0.1.5", action: "read" } },
  { level: "WARN", service: "audit-service", message: "Unusual access pattern: usr_100234 made 847 API calls in last 5 minutes", security: true, securityCategory: "network_anomaly", attributes: { user_id: "usr_100234", calls: "847", window: "5m", baseline: "50" } },
  { level: "ERROR", service: "audit-service", message: "CVE-2024-21626 detected in container image: notification-service:v1.12.0 (runc vulnerability)", security: true, securityCategory: "cve_alert", attributes: { cve: "CVE-2024-21626", image: "notification-service:v1.12.0", severity: "HIGH", component: "runc" } },
  { level: "WARN", service: "audit-service", message: "Network anomaly: unexpected outbound connection from payment-service to 198.51.100.42:4444", security: true, securityCategory: "network_anomaly", attributes: { source: "payment-service", destination: "198.51.100.42:4444", port: "4444", protocol: "TCP" } },
  { level: "ERROR", service: "audit-service", message: "Potential secret exposure: AWS access key pattern detected in response body of /api/v1/debug/env", security: true, securityCategory: "secret_exposure", attributes: { endpoint: "/api/v1/debug/env", pattern: "AKIA*", action: "blocked" } },
  { level: "FATAL", service: "audit-service", message: "Critical security alert: multiple privilege escalation attempts from IP 203.0.113.42 in last 10 minutes", security: true, securityCategory: "privilege_escalation", attributes: { source_ip: "203.0.113.42", attempts: "23", window: "10m", action: "ip_blocked" } },
  { level: "INFO", service: "audit-service", message: "Security scan completed: 0 critical, 2 high, 5 medium vulnerabilities found", attributes: { critical: "0", high: "2", medium: "5", low: "12", scan_type: "container_image" } },

  // More general entries for variety
  { level: "INFO", service: "api-gateway", message: "DELETE /api/v1/users/sessions 200 8ms - bulk session cleanup", hasTrace: true, attributes: { method: "DELETE", path: "/api/v1/users/sessions", status: "200", sessions_deleted: "147" } },
  { level: "INFO", service: "api-gateway", message: "PATCH /api/v1/users/usr_384712/settings 200 34ms", hasTrace: true, attributes: { method: "PATCH", path: "/api/v1/users/usr_384712/settings", status: "200", duration: "34ms" } },
  { level: "TRACE", service: "api-gateway", message: "Request headers: Host=api.aegis.dev, Accept=application/json, X-Request-Id=req_847291", attributes: { host: "api.aegis.dev", accept: "application/json", request_id: "req_847291" } },
  { level: "TRACE", service: "user-service", message: "SQL query plan: Seq Scan on users (cost=0.00..35.50 rows=2550)", attributes: { query_type: "EXPLAIN", cost: "35.50", rows: "2550" } },
  { level: "INFO", service: "auth-service", message: "MFA challenge sent: user=usr_384712 method=totp", hasTrace: true, attributes: { user_id: "usr_384712", mfa_method: "totp" } },
  { level: "INFO", service: "payment-service", message: "Subscription renewed: sub_847291 plan=pro next_billing=2026-05-10", hasTrace: true, attributes: { subscription_id: "sub_847291", plan: "pro", next_billing: "2026-05-10" } },
  { level: "WARN", service: "user-service", message: "Slow query detected: UPDATE user_sessions SET last_active = NOW() (2103ms)", attributes: { query_type: "UPDATE", table: "user_sessions", duration: "2103ms", threshold: "1000ms" } },
  { level: "ERROR", service: "notification-service", message: "Template rendering failed: unknown variable {{user.name}} in template order_confirmation", attributes: { template: "order_confirmation", error: "unknown_variable", variable: "user.name" } },
  { level: "INFO", service: "deployment-controller", message: "HPA scaled up: payment-service from 3 to 7 replicas (CPU utilization 82%)", attributes: { app: "payment-service", from_replicas: "3", to_replicas: "7", cpu_utilization: "82%" } },
  { level: "INFO", service: "config-service", message: "Feature flag toggled: feature_flags.new_checkout=disabled (user: admin@company.com)", attributes: { key: "feature_flags.new_checkout", value: "disabled", changed_by: "admin@company.com" } },

  // More security events
  { level: "WARN", service: "auth-service", message: "Brute force attempt detected: 15 failed logins from IP 198.51.100.23 in 2 minutes", security: true, securityCategory: "auth_failure", attributes: { source_ip: "198.51.100.23", failed_attempts: "15", window: "2m", action: "rate_limited" } },
  { level: "ERROR", service: "audit-service", message: "CVE-2024-3094 (xz-utils backdoor) detected in base image of auth-service:v3.2.1", security: true, securityCategory: "cve_alert", attributes: { cve: "CVE-2024-3094", image: "auth-service:v3.2.1", severity: "CRITICAL", component: "xz-utils" } },
  { level: "WARN", service: "audit-service", message: "Unauthorized API key usage: key api_key_expired_291847 used from new IP 172.16.0.99", security: true, securityCategory: "auth_failure", attributes: { api_key: "api_key_expired_291847", source_ip: "172.16.0.99", status: "expired" } },

  // Additional variety entries
  { level: "INFO", service: "api-gateway", message: "GET /api/v1/search?q=devops 200 156ms (cache MISS)", hasTrace: true, attributes: { method: "GET", path: "/api/v1/search", status: "200", duration: "156ms", cache: "MISS" } },
  { level: "INFO", service: "user-service", message: "User avatar uploaded: usr_384712 size=2.4MB format=webp", attributes: { user_id: "usr_384712", size: "2.4MB", format: "webp" } },
  { level: "INFO", service: "payment-service", message: "Daily reconciliation completed: 12,847 transactions, $1.2M total, 3 discrepancies", attributes: { transactions: "12847", total: "$1.2M", discrepancies: "3" } },
  { level: "INFO", service: "notification-service", message: "Batch email completed: 5,847 emails sent for campaign=spring_promo (98.2% delivered)", attributes: { campaign: "spring_promo", sent: "5847", delivery_rate: "98.2%" } },
  { level: "INFO", service: "api-gateway", message: "WebSocket connection established: ws_847291 user=usr_384712", hasTrace: true, attributes: { connection_id: "ws_847291", user_id: "usr_384712", protocol: "wss" } },
  { level: "WARN", service: "api-gateway", message: "Request body too large: POST /api/v1/uploads rejected (52MB > 10MB limit)", attributes: { method: "POST", path: "/api/v1/uploads", size: "52MB", limit: "10MB" } },
  { level: "DEBUG", service: "auth-service", message: "RBAC policy evaluated: user=usr_291847 resource=/api/v1/admin action=read result=deny", attributes: { user_id: "usr_291847", resource: "/api/v1/admin", action: "read", result: "deny" } },
  { level: "INFO", service: "deployment-controller", message: "Pod readiness probe passed: payment-service-7b8f9c-x4k2p (attempt 1/3)", attributes: { pod: "payment-service-7b8f9c-x4k2p", probe: "readiness", attempt: "1", max_attempts: "3" } },
  { level: "INFO", service: "config-service", message: "Terraform state lock acquired: workspace=production lock_id=lock_847291", attributes: { workspace: "production", lock_id: "lock_847291" } },
  { level: "INFO", service: "config-service", message: "Terraform plan: 2 to add, 1 to change, 0 to destroy (workspace: production)", attributes: { to_add: "2", to_change: "1", to_destroy: "0", workspace: "production" } },
  { level: "INFO", service: "api-gateway", message: "Circuit breaker opened for payment-service: error rate 34% exceeds threshold 25%", attributes: { service: "payment-service", error_rate: "34%", threshold: "25%", state: "open" } },
  { level: "INFO", service: "api-gateway", message: "Circuit breaker half-open for payment-service: testing with 10% traffic", attributes: { service: "payment-service", state: "half-open", traffic_percentage: "10%" } },
  { level: "INFO", service: "api-gateway", message: "Circuit breaker closed for payment-service: error rate normalized to 0.5%", attributes: { service: "payment-service", error_rate: "0.5%", state: "closed" } },
  { level: "WARN", service: "payment-service", message: "PCI DSS compliance check: TLS 1.0 connection attempt from 10.0.4.12 - rejected", security: true, securityCategory: "network_anomaly", attributes: { source_ip: "10.0.4.12", tls_version: "1.0", action: "rejected" } },
  { level: "INFO", service: "audit-service", message: "Data retention policy executed: 2,847,291 log entries archived to S3 Glacier", attributes: { archived: "2847291", destination: "s3-glacier", policy: "90-day-retention" } },
  { level: "DEBUG", service: "notification-service", message: "FCM token refreshed for device android_384712", attributes: { device_type: "android", device_id: "android_384712", provider: "fcm" } },
  { level: "INFO", service: "user-service", message: "GDPR data export completed for usr_291847 (47 tables, 12.3MB)", attributes: { user_id: "usr_291847", tables: "47", export_size: "12.3MB", format: "json" } },
  { level: "ERROR", service: "api-gateway", message: "POST /api/v1/graphql 500 Internal Server Error - resolver panic in UserQuery.friends", hasTrace: true, attributes: { method: "POST", path: "/api/v1/graphql", status: "500", error: "resolver_panic", resolver: "UserQuery.friends" } },
  { level: "INFO", service: "deployment-controller", message: "Node pool scaled: production-pool from 5 to 8 nodes (pending pods: 12)", attributes: { pool: "production-pool", from_nodes: "5", to_nodes: "8", pending_pods: "12" } },
  { level: "WARN", service: "user-service", message: "Replication lag detected: replica-2 is 4.7s behind primary", attributes: { replica: "replica-2", lag: "4.7s", threshold: "3s" } },
  { level: "INFO", service: "auth-service", message: "SSO session created: user=sarah@partner.co provider=okta session=sess_847291", hasTrace: true, attributes: { user: "sarah@partner.co", provider: "okta", session_id: "sess_847291" } },
  { level: "INFO", service: "payment-service", message: "Currency exchange rate updated: USD/EUR=0.9234 provider=ecb timestamp=2026-04-10T08:00:00Z", attributes: { pair: "USD/EUR", rate: "0.9234", provider: "ecb" } },
  { level: "TRACE", service: "payment-service", message: "gRPC call: PaymentService.ProcessPayment request_size=1.2KB response_size=0.4KB", attributes: { service: "PaymentService", method: "ProcessPayment", request_size: "1.2KB", response_size: "0.4KB" } },
]

// Generate 120 log entries by cycling through templates with unique timestamps
export const MOCK_LOGS: LogEntry[] = Array.from({ length: 120 }, (_, i) => {
  const template = LOG_TEMPLATES[i % LOG_TEMPLATES.length]
  const traceId = template.hasTrace ? generateTraceId() : undefined
  const spanId = template.hasTrace ? generateSpanId() : undefined

  return {
    id: generateId(i),
    timestamp: generateTimestamp(i, 120),
    level: template.level,
    service: template.service,
    message: template.message,
    traceId,
    spanId,
    attributes: {
      ...(template.attributes || {}),
      hostname: `${template.service}-${Math.floor(Math.random() * 5)}-${Math.random().toString(36).slice(2, 7)}`,
      namespace: "production",
      cluster: "aegis-prod-01",
    },
    security: template.security,
    securityCategory: template.securityCategory,
  }
})

// Helper to get log stats
export function getLogStats(logs: LogEntry[]) {
  const total = logs.length
  const errors = logs.filter((l) => l.level === "ERROR" || l.level === "FATAL").length
  const warnings = logs.filter((l) => l.level === "WARN").length
  const securityEvents = logs.filter((l) => l.security).length

  return { total, errors, warnings, securityEvents }
}

// Log level colors for consistent theming
export const LOG_LEVEL_CONFIG: Record<LogLevel, { color: string; bgColor: string; label: string }> = {
  FATAL: { color: "#FF0040", bgColor: "rgba(255, 0, 64, 0.15)", label: "FTL" },
  ERROR: { color: "#FF4444", bgColor: "rgba(255, 68, 68, 0.15)", label: "ERR" },
  WARN: { color: "#FFB020", bgColor: "rgba(255, 176, 32, 0.15)", label: "WRN" },
  INFO: { color: "#00FF88", bgColor: "rgba(0, 255, 136, 0.15)", label: "INF" },
  DEBUG: { color: "#666666", bgColor: "rgba(102, 102, 102, 0.15)", label: "DBG" },
  TRACE: { color: "#444444", bgColor: "rgba(68, 68, 68, 0.15)", label: "TRC" },
}
