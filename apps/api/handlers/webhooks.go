package handlers

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/JIUNG9/sre-knowledge-engine/apps/api/mock"
	"github.com/JIUNG9/sre-knowledge-engine/apps/api/models"
)

// alertStore provides thread-safe in-memory storage for alerts.
var alertStore = struct {
	sync.RWMutex
	data []models.Alert
}{
	data: mock.Alerts(),
}

// WebhookHandlers holds dependencies for webhook handlers.
type WebhookHandlers struct {
	Logger *zap.Logger
}

// NewWebhookHandlers creates a new WebhookHandlers instance.
func NewWebhookHandlers(logger *zap.Logger) *WebhookHandlers {
	return &WebhookHandlers{Logger: logger}
}

// severityFromLabels extracts severity from alert labels, defaulting to medium.
func severityFromLabels(labels map[string]string) models.Severity {
	if sev, ok := labels["severity"]; ok {
		switch sev {
		case "critical":
			return models.SeverityCritical
		case "high", "warning":
			return models.SeverityHigh
		case "medium", "info":
			return models.SeverityMedium
		case "low":
			return models.SeverityLow
		}
	}
	return models.SeverityMedium
}

// serviceFromLabels extracts the service name from labels.
func serviceFromLabels(labels map[string]string) string {
	for _, key := range []string{"service", "job", "namespace", "app"} {
		if v, ok := labels[key]; ok {
			return v
		}
	}
	return "unknown"
}

// alertStatusFromString converts an Alertmanager status string to an AlertStatus.
func alertStatusFromString(s string) models.AlertStatus {
	if s == "resolved" {
		return models.AlertStatusResolved
	}
	return models.AlertStatusFiring
}

// storeAlert adds or updates an alert by fingerprint for deduplication.
func storeAlert(alert models.Alert) {
	alertStore.Lock()
	defer alertStore.Unlock()

	// Deduplicate by fingerprint — update if exists.
	for i := range alertStore.data {
		if alertStore.data[i].Fingerprint == alert.Fingerprint {
			alertStore.data[i].Status = alert.Status
			alertStore.data[i].EndsAt = alert.EndsAt
			return
		}
	}
	alertStore.data = append(alertStore.data, alert)
}

// HandleSigNoz receives webhooks from SigNoz / Alertmanager.
// SigNoz uses the Alertmanager webhook format.
func (h *WebhookHandlers) HandleSigNoz(c *fiber.Ctx) error {
	var payload models.AlertmanagerPayload
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.Logger.Warn("Failed to parse SigNoz webhook payload", zap.Error(err))
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_payload",
			"message": "Failed to parse Alertmanager payload",
		})
	}

	h.Logger.Info("Received SigNoz/Alertmanager webhook",
		zap.Int("alert_count", len(payload.Alerts)),
		zap.String("status", payload.Status),
	)

	processed := 0
	for _, a := range payload.Alerts {
		fingerprint := a.Fingerprint
		if fingerprint == "" {
			fingerprint = generateFingerprint(a.Labels)
		}

		title := a.Labels["alertname"]
		if title == "" {
			title = "SigNoz Alert"
		}

		description := a.Annotations["summary"]
		if description == "" {
			description = a.Annotations["description"]
		}

		alert := models.Alert{
			ID:          fmt.Sprintf("ALT-%s", uuid.New().String()[:8]),
			Source:      models.AlertSourceSigNoz,
			Title:       title,
			Description: description,
			Severity:    severityFromLabels(a.Labels),
			Service:     serviceFromLabels(a.Labels),
			Status:      alertStatusFromString(a.Status),
			Labels:      a.Labels,
			Annotations: a.Annotations,
			StartsAt:    a.StartsAt,
			Fingerprint: fingerprint,
		}

		if a.Status == "resolved" && !a.EndsAt.IsZero() {
			alert.EndsAt = &a.EndsAt
		}

		storeAlert(alert)
		processed++
	}

	return c.JSON(fiber.Map{
		"status":    "received",
		"source":    "signoz",
		"processed": processed,
	})
}

// datadogTags turns Datadog tags into labels. Tags arrive either as the
// comma-separated string from the webhook's $TAGS variable or as a JSON array.
// "key:value" becomes a label; a bare tag becomes a label with value "true".
// Only the first colon splits, so "url:http://x" keeps its value. When a key
// repeats ("env:a,env:b") the first value wins.
func datadogTags(v interface{}) map[string]string {
	var list []string
	switch t := v.(type) {
	case string:
		list = strings.Split(t, ",")
	case []interface{}:
		for _, e := range t {
			if s, ok := e.(string); ok {
				list = append(list, s)
			}
		}
	}

	labels := map[string]string{}
	for _, tag := range list {
		tag = strings.TrimSpace(tag)
		if tag == "" {
			continue
		}
		key, val, found := strings.Cut(tag, ":")
		key = strings.TrimSpace(key)
		if key == "" {
			continue
		}
		if !found {
			val = "true"
		}
		if _, exists := labels[key]; !exists {
			labels[key] = strings.TrimSpace(val)
		}
	}
	return labels
}

// datadogSeverity maps a Datadog payload to a severity. The monitor priority
// (P1-P5, or 1-5) wins over alert_type, since priority is set by the team and
// alert_type only says whether the monitor is in alert or warn. Unknown or
// missing values give medium.
func datadogSeverity(priority, alertType string) models.Severity {
	switch strings.ToLower(strings.TrimSpace(priority)) {
	case "p1", "1":
		return models.SeverityCritical
	case "p2", "2":
		return models.SeverityHigh
	case "p3", "3", "normal":
		return models.SeverityMedium
	case "p4", "4", "p5", "5", "low":
		return models.SeverityLow
	}
	switch strings.ToLower(strings.TrimSpace(alertType)) {
	case "error":
		return models.SeverityHigh
	case "warning":
		return models.SeverityMedium
	case "info", "success":
		return models.SeverityLow
	}
	return models.SeverityMedium
}

// datadogString reads a payload field that may be a string or a number, since
// webhook templates quote $PRIORITY in some setups and not in others.
func datadogString(raw map[string]interface{}, key string) string {
	switch v := raw[key].(type) {
	case string:
		return v
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	}
	return ""
}

// HandleDatadog receives webhooks from Datadog. The payload is whatever the
// webhook integration's template produces; this reads title, body, id, tags,
// priority and alert_type (map them to $EVENT_TITLE, $EVENT_MSG, $ID, $TAGS,
// $ALERT_PRIORITY and $ALERT_TYPE).
func (h *WebhookHandlers) HandleDatadog(c *fiber.Ctx) error {
	var raw map[string]interface{}
	if err := json.Unmarshal(c.Body(), &raw); err != nil {
		h.Logger.Warn("Failed to parse Datadog webhook payload", zap.Error(err))
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_payload",
			"message": "Failed to parse Datadog payload",
		})
	}

	h.Logger.Info("Received Datadog webhook",
		zap.Int("payload_size", len(c.Body())),
	)

	title, _ := raw["title"].(string)
	if title == "" {
		title = "Datadog Alert"
	}

	body, _ := raw["body"].(string)
	alertID, _ := raw["id"].(string)
	if alertID == "" {
		alertID = uuid.New().String()[:8]
	}

	tags := datadogTags(raw["tags"])

	alert := models.Alert{
		ID:          fmt.Sprintf("ALT-%s", alertID),
		Source:      models.AlertSourceDatadog,
		Title:       title,
		Description: body,
		Severity:    datadogSeverity(datadogString(raw, "priority"), datadogString(raw, "alert_type")),
		Service:     serviceFromLabels(tags),
		Status:      models.AlertStatusFiring,
		Labels:      tags,
		StartsAt:    time.Now().UTC(),
		Fingerprint: fmt.Sprintf("dd-%s", alertID),
	}

	storeAlert(alert)

	return c.JSON(fiber.Map{
		"status":    "received",
		"source":    "datadog",
		"processed": 1,
	})
}

// HandlePrometheus receives webhooks from Prometheus Alertmanager.
func (h *WebhookHandlers) HandlePrometheus(c *fiber.Ctx) error {
	var payload models.AlertmanagerPayload
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.Logger.Warn("Failed to parse Prometheus Alertmanager payload", zap.Error(err))
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_payload",
			"message": "Failed to parse Alertmanager payload",
		})
	}

	h.Logger.Info("Received Prometheus Alertmanager webhook",
		zap.Int("alert_count", len(payload.Alerts)),
		zap.String("group_key", payload.GroupKey),
		zap.String("status", payload.Status),
	)

	processed := 0
	for _, a := range payload.Alerts {
		fingerprint := a.Fingerprint
		if fingerprint == "" {
			fingerprint = generateFingerprint(a.Labels)
		}

		title := a.Labels["alertname"]
		if title == "" {
			title = "Prometheus Alert"
		}

		description := a.Annotations["summary"]
		if description == "" {
			description = a.Annotations["description"]
		}

		alert := models.Alert{
			ID:          fmt.Sprintf("ALT-%s", uuid.New().String()[:8]),
			Source:      models.AlertSourcePrometheus,
			Title:       title,
			Description: description,
			Severity:    severityFromLabels(a.Labels),
			Service:     serviceFromLabels(a.Labels),
			Status:      alertStatusFromString(a.Status),
			Labels:      a.Labels,
			Annotations: a.Annotations,
			StartsAt:    a.StartsAt,
			Fingerprint: fingerprint,
		}

		if a.Status == "resolved" && !a.EndsAt.IsZero() {
			alert.EndsAt = &a.EndsAt
		}

		storeAlert(alert)
		processed++
	}

	return c.JSON(fiber.Map{
		"status":    "received",
		"source":    "prometheus",
		"processed": processed,
	})
}

// ListAlerts returns all stored alerts, sorted by most recent first.
func ListAlerts(c *fiber.Ctx) error {
	sourceFilter := c.Query("source")
	statusFilter := c.Query("status")
	serviceFilter := c.Query("service")

	alertStore.RLock()
	defer alertStore.RUnlock()

	var filtered []models.Alert
	for _, a := range alertStore.data {
		if sourceFilter != "" && string(a.Source) != sourceFilter {
			continue
		}
		if statusFilter != "" && string(a.Status) != statusFilter {
			continue
		}
		if serviceFilter != "" && a.Service != serviceFilter {
			continue
		}
		filtered = append(filtered, a)
	}

	if filtered == nil {
		filtered = []models.Alert{}
	}

	// Sort by StartsAt descending (most recent first).
	sort.Slice(filtered, func(i, j int) bool {
		return filtered[i].StartsAt.After(filtered[j].StartsAt)
	})

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// GetAlertFeed returns the last 50 alerts as a feed, sorted most recent first.
func GetAlertFeed(c *fiber.Ctx) error {
	alertStore.RLock()
	defer alertStore.RUnlock()

	// Copy and sort by StartsAt descending.
	sorted := make([]models.Alert, len(alertStore.data))
	copy(sorted, alertStore.data)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].StartsAt.After(sorted[j].StartsAt)
	})

	limit := 50
	if len(sorted) > limit {
		sorted = sorted[:limit]
	}

	return c.JSON(fiber.Map{
		"data":  sorted,
		"total": len(sorted),
	})
}

// generateFingerprint creates a deterministic fingerprint from alert labels.
func generateFingerprint(labels map[string]string) string {
	// Sort keys for deterministic output.
	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var b []byte
	for _, k := range keys {
		// Quote both sides so a label containing "=" or "," can't alias another
		// label set ({"a":"b=c"} and {"a=b":"c"} must not hash alike).
		b = append(b, []byte(strconv.Quote(k)+"="+strconv.Quote(labels[k])+",")...)
	}
	hash := sha256.Sum256(b)
	return fmt.Sprintf("%x", hash[:8])
}
