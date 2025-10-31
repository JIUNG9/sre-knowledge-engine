package mock

import (
	"fmt"
	"math/rand"
	"time"

	"github.com/junegu/aegis/api/models"
)

// Services is the list of services that generate mock logs.
var Services = []string{
	"api-gateway",
	"auth-service",
	"user-service",
	"payment-service",
	"notification-service",
	"deployment-controller",
}

// levelWeights defines the weighted distribution of log levels.
// 60% info, 20% debug, 10% warn, 7% error, 2% fatal, 1% trace
var levelWeights = []struct {
	level  string
	weight int
}{
	{"info", 60},
	{"debug", 20},
	{"warn", 10},
	{"error", 7},
	{"fatal", 2},
	{"trace", 1},
}

var totalWeight int

func init() {
	for _, lw := range levelWeights {
		totalWeight += lw.weight
	}
}

// pickLevel returns a random log level based on weighted distribution.
func pickLevel() string {
	r := rand.Intn(totalWeight)
	cumulative := 0
	for _, lw := range levelWeights {
		cumulative += lw.weight
		if r < cumulative {
			return lw.level
		}
	}
	return "info"
}

// messageTemplates maps services to realistic log message generators.
var messageTemplates = map[string]map[string][]string{
	"api-gateway": {
		"info": {
			"GET /api/v1/users 200 12ms",
			"POST /api/v1/orders 201 45ms",
			"GET /api/v1/products?page=2 200 23ms",
			"PUT /api/v1/users/1234/profile 200 31ms",
			"GET /api/v1/health 200 1ms",
			"DELETE /api/v1/sessions/abc123 204 8ms",
		},
		"debug": {
			"Routing request to upstream: user-service:8080",
			"Rate limit check passed for IP 10.0.1.42 (78/100 requests)",
			"Cache HIT for key: products:page:2 TTL=45s",
			"Connection pool stats: active=23 idle=7 total=30",
		},
		"warn": {
			"GET /api/v1/search 200 1523ms - slow response",
			"Rate limit approaching for IP 203.0.113.15 (95/100 requests)",
			"Upstream auth-service response time degraded: avg 850ms",
			"Request body size 4.2MB exceeds recommended limit 1MB",
		},
		"error": {
			"POST /api/v1/payments 502 - upstream connection refused",
			"GET /api/v1/orders/5678 500 - internal server error",
			"Circuit breaker OPEN for payment-service after 5 consecutive failures",
			"TLS handshake failed with upstream notification-service: certificate expired",
		},
		"fatal": {
			"Unable to bind to port 8080: address already in use",
			"Out of memory: cannot allocate request buffer",
		},
		"trace": {
			"Header forwarding: X-Request-ID=req-a1b2c3, X-Trace-ID=tr-abc123",
		},
	},
	"auth-service": {
		"info": {
			"User login successful: user_id=usr_1234 method=password",
			"Token refreshed for user_id=usr_5678 expires_in=3600s",
			"OAuth2 callback received from provider=google",
			"API key validated for service=payment-service",
			"Session created: session_id=sess_abc123 user_id=usr_1234",
		},
		"debug": {
			"JWT claims validated: sub=usr_1234 exp=1712800000 iss=aegis",
			"OIDC discovery document fetched from https://accounts.google.com/.well-known/openid-configuration",
			"Password hash verified in 12ms using argon2id",
		},
		"warn": {
			"Failed login attempt from IP 203.0.113.42 for user admin@company.com (attempt 3/5)",
			"Token near expiry: user_id=usr_9012 remaining=120s",
			"Unusual login location detected: user_id=usr_5678 country=RU previous=US",
			"Failed login attempt from IP 203.0.113.88 for user root@company.com (attempt 5/5)",
		},
		"error": {
			"Failed login attempt from IP 203.0.113.100 - account locked after 5 attempts",
			"Permission denied: user usr_3456 lacks role admin for resource /admin/settings",
			"OAuth2 token exchange failed: invalid_grant - authorization code expired",
			"LDAP connection failed: unable to reach ldap.internal:636",
		},
		"fatal": {
			"Signing key rotation failed: HSM unavailable",
		},
		"trace": {
			"RBAC policy evaluation: user=usr_1234 resource=/api/users action=read result=allow",
		},
	},
	"user-service": {
		"info": {
			"User profile updated: user_id=usr_1234 fields=[name,avatar]",
			"New user registered: user_id=usr_9999 email=new@example.com",
			"User preferences saved: user_id=usr_5678 theme=dark",
			"Bulk user export completed: 1523 records in 2.3s",
		},
		"debug": {
			"DB query: SELECT * FROM users WHERE id = $1 [usr_1234] took 3ms",
			"Cache MISS for user:usr_5678 - fetching from database",
			"Pagination: page=3 per_page=25 total=1523 has_next=true",
		},
		"warn": {
			"Slow query detected: SELECT * FROM users WHERE email = $1 took 2.3s",
			"User avatar upload 8.5MB exceeds recommended 5MB limit",
			"Deprecated endpoint /api/v1/users/search called by client v1.2.0",
		},
		"error": {
			"Failed to update user profile: constraint violation on email (duplicate)",
			"Database connection pool exhausted: 50/50 connections in use",
			"User avatar processing failed: unsupported image format .webp",
		},
		"fatal": {
			"Database migration failed: column 'preferences' already exists",
		},
		"trace": {
			"ORM query plan: sequential scan on users table, estimated rows=15000",
		},
	},
	"payment-service": {
		"info": {
			"Payment processed: order_id=ord_7890 amount=$149.99 method=stripe",
			"Refund issued: order_id=ord_4567 amount=$29.99 reason=customer_request",
			"Subscription renewed: user_id=usr_1234 plan=pro next_billing=2026-05-10",
			"Invoice generated: invoice_id=inv_2345 total=$299.00",
		},
		"debug": {
			"Stripe API call: POST /v1/charges took 234ms",
			"Idempotency key checked: key=idem_abc123 status=new",
			"Tax calculation: subtotal=$149.99 tax_rate=0.08 tax=$12.00 total=$161.99",
		},
		"warn": {
			"Payment retry scheduled: order_id=ord_8901 attempt=2/3 next_retry=60s",
			"Stripe webhook signature verification took 450ms (threshold: 500ms)",
			"Currency conversion rate stale: last_updated=2h ago",
		},
		"error": {
			"Payment failed: order_id=ord_3456 error=card_declined issuer=stripe",
			"Webhook delivery failed to https://partner.example.com/hooks: timeout after 30s",
			"Duplicate charge detected: order_id=ord_7890 charge_id=ch_abc - reverting",
		},
		"fatal": {
			"Payment queue consumer crashed: kafka broker connection lost",
		},
		"trace": {
			"PCI audit log: card_last4=4242 action=authorize merchant_id=m_001",
		},
	},
	"notification-service": {
		"info": {
			"Email sent: to=user@example.com template=welcome delivery_id=del_123",
			"Push notification delivered: user_id=usr_5678 device=ios",
			"SMS sent: to=+1234567890 provider=twilio status=delivered",
			"Notification batch completed: 250 emails, 180 push, 45 SMS",
		},
		"debug": {
			"Template rendered: welcome_email variables={name:John, plan:Pro}",
			"FCM token validated for device_id=dev_abc123",
			"Email queue depth: 42 pending, 3 in-flight, avg_latency=1.2s",
		},
		"warn": {
			"Email bounce: to=invalid@example.com type=hard_bounce",
			"Push notification token expired for user_id=usr_3456 device_id=dev_old",
			"SMS delivery rate approaching limit: 48/50 per second",
		},
		"error": {
			"Failed to send email: SMTP connection refused to smtp.provider.com:587",
			"Push notification failed: FCM error=InvalidRegistration device_id=dev_xyz",
			"Unusual network access pattern detected from IP 198.51.100.23",
		},
		"fatal": {
			"Template engine initialization failed: missing required template directory",
		},
		"trace": {
			"SMTP handshake: EHLO aegis.local -> 250 smtp.provider.com STARTTLS",
		},
	},
	"deployment-controller": {
		"info": {
			"Deployment started: app=user-service version=v2.3.1 strategy=rolling",
			"Deployment completed: app=payment-service version=v1.8.0 duration=45s",
			"Rollback initiated: app=api-gateway from=v3.0.1 to=v3.0.0",
			"Health check passed: app=auth-service pod=auth-7b4d9f-xyz ready=true",
			"Scaling event: app=notification-service replicas 3 -> 5 reason=cpu_threshold",
		},
		"debug": {
			"K8s API: GET /apis/apps/v1/namespaces/prod/deployments/user-service took 15ms",
			"Pod scheduling: pod=payment-7c8d3f-abc node=worker-03 zone=us-east-1a",
			"Container image pull: registry.internal/user-service:v2.3.1 size=142MB took 8s",
		},
		"warn": {
			"Pod restart detected: app=payment-service pod=payment-6f7e8d-def restarts=3",
			"Node resource pressure: worker-05 memory_usage=87% threshold=85%",
			"Deployment stalled: app=auth-service waiting for 2/5 pods to be ready (timeout in 120s)",
		},
		"error": {
			"Deployment failed: app=notification-service error=ImagePullBackOff image=registry.internal/notification:v2.0.0-bad",
			"Liveness probe failed: app=user-service pod=user-5a6b7c-ghi endpoint=/health status=503",
			"Permission denied: user lacks role admin for namespace production",
		},
		"fatal": {
			"Cluster connection lost: unable to reach kube-apiserver at https://k8s.internal:6443",
		},
		"trace": {
			"K8s watch event: MODIFIED deployment/user-service generation=42 replicas=3/3",
		},
	},
}

// securityMessages are additional security-themed log messages injected randomly.
var securityMessages = []models.LogEntry{
	{Level: "warn", Service: "auth-service", Message: "Failed login attempt from IP 203.0.113.42 for user admin@company.com (brute force suspected)"},
	{Level: "error", Service: "auth-service", Message: "Permission denied: user usr_3456 lacks role admin for resource /admin/users/delete"},
	{Level: "warn", Service: "api-gateway", Message: "Unusual network access pattern detected from IP 198.51.100.15 - 500 requests in 10s"},
	{Level: "error", Service: "auth-service", Message: "Failed login attempt from IP 203.0.113.77 - IP added to temporary blocklist"},
	{Level: "warn", Service: "deployment-controller", Message: "Unauthorized kubectl exec attempt: user=dev-intern namespace=production pod=payment-7c8d3f-abc"},
	{Level: "error", Service: "api-gateway", Message: "SQL injection attempt detected: query parameter contains 'OR 1=1' from IP 203.0.113.99"},
	{Level: "warn", Service: "notification-service", Message: "Unusual network access pattern detected from IP 192.0.2.100 - accessing internal endpoints"},
	{Level: "error", Service: "auth-service", Message: "Certificate validation failed: client cert expired for service payment-service"},
}

// GenerateMockLogs generates a slice of realistic mock log entries.
func GenerateMockLogs(count int) []models.LogEntry {
	entries := make([]models.LogEntry, 0, count)
	now := time.Now()

	for i := 0; i < count; i++ {
		// Inject a security event roughly 5% of the time.
		if rand.Intn(100) < 5 {
			secEntry := securityMessages[rand.Intn(len(securityMessages))]
			secEntry.Timestamp = now.Add(-time.Duration(rand.Intn(3600)) * time.Second)
			secEntry.TraceID = fmt.Sprintf("tr-%s", randomHex(12))
			secEntry.SpanID = fmt.Sprintf("sp-%s", randomHex(8))
			secEntry.Attributes = map[string]string{
				"env":    "production",
				"region": randomRegion(),
			}
			entries = append(entries, secEntry)
			continue
		}

		service := Services[rand.Intn(len(Services))]
		level := pickLevel()

		message := pickMessage(service, level)

		entry := models.LogEntry{
			Timestamp: now.Add(-time.Duration(rand.Intn(3600)) * time.Second),
			Level:     level,
			Message:   message,
			Service:   service,
			TraceID:   fmt.Sprintf("tr-%s", randomHex(12)),
			SpanID:    fmt.Sprintf("sp-%s", randomHex(8)),
			Attributes: map[string]string{
				"env":    pickEnv(),
				"region": randomRegion(),
			},
		}
		entries = append(entries, entry)
	}

	return entries
}

// GenerateSingleMockLog generates a single realistic mock log entry.
func GenerateSingleMockLog() models.LogEntry {
	logs := GenerateMockLogs(1)
	return logs[0]
}

// pickMessage selects a random message for the given service and level.
func pickMessage(service, level string) string {
	svcMessages, ok := messageTemplates[service]
	if !ok {
		return fmt.Sprintf("[%s] Generic log message from %s", level, service)
	}
	levelMessages, ok := svcMessages[level]
	if !ok {
		// Fall back to info messages if no messages exist for this level.
		levelMessages = svcMessages["info"]
		if len(levelMessages) == 0 {
			return fmt.Sprintf("[%s] Log message from %s", level, service)
		}
	}
	return levelMessages[rand.Intn(len(levelMessages))]
}

// randomHex generates a random hex string of the given length.
func randomHex(length int) string {
	const hexChars = "0123456789abcdef"
	b := make([]byte, length)
	for i := range b {
		b[i] = hexChars[rand.Intn(len(hexChars))]
	}
	return string(b)
}

// randomRegion returns a random AWS region.
func randomRegion() string {
	regions := []string{"us-east-1", "us-west-2", "eu-west-1", "ap-northeast-2"}
	return regions[rand.Intn(len(regions))]
}

// pickEnv returns a random environment, heavily weighted to production.
func pickEnv() string {
	r := rand.Intn(100)
	if r < 80 {
		return "production"
	} else if r < 95 {
		return "staging"
	}
	return "development"
}
