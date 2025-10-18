package handlers

import (
	"time"

	"github.com/gofiber/fiber/v2"
)

// LogEntry represents a single log entry.
type LogEntry struct {
	Timestamp time.Time         `json:"timestamp"`
	Level     string            `json:"level"`
	Service   string            `json:"service"`
	Message   string            `json:"message"`
	TraceID   string            `json:"trace_id,omitempty"`
	SpanID    string            `json:"span_id,omitempty"`
	Labels    map[string]string `json:"labels,omitempty"`
}

// Mock log data for development.
var mockLogs = []LogEntry{
	{
		Timestamp: time.Date(2026, 4, 10, 10, 5, 23, 0, time.UTC),
		Level:     "error",
		Service:   "payment-service",
		Message:   "Failed to process payment: connection refused to payment gateway",
		TraceID:   "abc123def456",
		SpanID:    "span-001",
		Labels:    map[string]string{"env": "production", "region": "us-east-1"},
	},
	{
		Timestamp: time.Date(2026, 4, 10, 10, 5, 24, 0, time.UTC),
		Level:     "warn",
		Service:   "user-service",
		Message:   "Slow query detected: SELECT * FROM users WHERE email = ? took 2.3s",
		TraceID:   "def789ghi012",
		SpanID:    "span-002",
		Labels:    map[string]string{"env": "production", "region": "us-east-1"},
	},
	{
		Timestamp: time.Date(2026, 4, 10, 10, 5, 25, 0, time.UTC),
		Level:     "info",
		Service:   "gateway",
		Message:   "Health check passed for upstream service: auth-service",
		Labels:    map[string]string{"env": "production"},
	},
}

// QueryLogs returns log entries matching the query parameters.
func QueryLogs(c *fiber.Ctx) error {
	// Placeholder: in production, this would query SigNoz/Loki/Elasticsearch.
	service := c.Query("service")
	level := c.Query("level")

	filtered := make([]LogEntry, 0, len(mockLogs))
	for _, log := range mockLogs {
		if service != "" && log.Service != service {
			continue
		}
		if level != "" && log.Level != level {
			continue
		}
		filtered = append(filtered, log)
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// StreamLogs is a placeholder for WebSocket-based log streaming.
func StreamLogs(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"message": "WebSocket log streaming endpoint — connect via ws:// protocol",
		"status":  "placeholder",
	})
}
