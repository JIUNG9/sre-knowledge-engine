package handlers

import (
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"

	"github.com/junegu/aegis/api/models"
)

// integrationStore provides thread-safe in-memory storage for integrations.
var integrationStore = struct {
	sync.RWMutex
	data []models.Integration
}{
	data: []models.Integration{
		{ID: "signoz", Name: "SigNoz", Category: "monitoring", Status: "not_configured"},
		{ID: "datadog", Name: "Datadog", Category: "monitoring", Status: "not_configured"},
		{ID: "prometheus", Name: "Prometheus", Category: "monitoring", Status: "not_configured"},
		{ID: "slack", Name: "Slack", Category: "notification", Status: "not_configured"},
		{ID: "jira", Name: "JIRA", Category: "ticketing", Status: "not_configured"},
		{ID: "github", Name: "GitHub", Category: "ticketing", Status: "not_configured"},
		{ID: "argocd", Name: "ArgoCD", Category: "deployment", Status: "not_configured"},
		{ID: "trivy", Name: "Trivy", Category: "security", Status: "not_configured"},
	},
}

// maskConfig returns a copy of the config with secret values masked.
func maskConfig(config map[string]string) map[string]string {
	if config == nil {
		return nil
	}
	masked := make(map[string]string, len(config))
	for k, v := range config {
		lower := strings.ToLower(k)
		if strings.Contains(lower, "key") || strings.Contains(lower, "secret") ||
			strings.Contains(lower, "token") || strings.Contains(lower, "password") {
			if len(v) > 8 {
				masked[k] = v[:4] + "..." + v[len(v)-4:]
			} else if len(v) > 0 {
				masked[k] = "****"
			} else {
				masked[k] = ""
			}
		} else {
			masked[k] = v
		}
	}
	return masked
}

// ListIntegrations returns all integrations with masked config values.
func ListIntegrations(c *fiber.Ctx) error {
	categoryFilter := c.Query("category")

	integrationStore.RLock()
	defer integrationStore.RUnlock()

	var result []models.Integration
	for _, integ := range integrationStore.data {
		if categoryFilter != "" && integ.Category != categoryFilter {
			continue
		}
		// Return a copy with masked config.
		copy := models.Integration{
			ID:        integ.ID,
			Name:      integ.Name,
			Category:  integ.Category,
			Status:    integ.Status,
			Config:    maskConfig(integ.Config),
			LastSync:  integ.LastSync,
			LastError: integ.LastError,
		}
		result = append(result, copy)
	}

	if result == nil {
		result = []models.Integration{}
	}

	return c.JSON(fiber.Map{
		"data":  result,
		"total": len(result),
	})
}

// UpdateIntegration updates the configuration for an integration.
func UpdateIntegration(c *fiber.Ctx) error {
	id := c.Params("id")

	var req models.UpdateIntegrationRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	integrationStore.Lock()
	defer integrationStore.Unlock()

	var found *models.Integration
	for i := range integrationStore.data {
		if integrationStore.data[i].ID == id {
			found = &integrationStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Integration not found",
		})
	}

	found.Config = req.Config
	if len(req.Config) > 0 {
		found.Status = "connected"
	}

	// Return a copy with masked config.
	result := models.Integration{
		ID:        found.ID,
		Name:      found.Name,
		Category:  found.Category,
		Status:    found.Status,
		Config:    maskConfig(found.Config),
		LastSync:  found.LastSync,
		LastError: found.LastError,
	}

	return c.JSON(result)
}

// TestIntegrationConnection simulates testing connectivity to an integration.
func TestIntegrationConnection(c *fiber.Ctx) error {
	id := c.Params("id")

	integrationStore.RLock()
	var found *models.Integration
	for i := range integrationStore.data {
		if integrationStore.data[i].ID == id {
			found = &integrationStore.data[i]
			break
		}
	}
	integrationStore.RUnlock()

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Integration not found",
		})
	}

	// Simulate a 1-2 second connection test delay.
	delay := time.Duration(1000+rand.Intn(1000)) * time.Millisecond
	time.Sleep(delay)

	// Update last sync time on successful test.
	now := time.Now().UTC()
	integrationStore.Lock()
	for i := range integrationStore.data {
		if integrationStore.data[i].ID == id {
			integrationStore.data[i].LastSync = &now
			integrationStore.data[i].LastError = ""
			if integrationStore.data[i].Status != "not_configured" {
				integrationStore.data[i].Status = "connected"
			}
			break
		}
	}
	integrationStore.Unlock()

	return c.JSON(models.ConnectionTestResult{
		Success: true,
		Message: "Successfully connected to " + found.Name,
		Latency: int(delay.Milliseconds()),
	})
}

// DisconnectIntegration resets an integration to not_configured status.
func DisconnectIntegration(c *fiber.Ctx) error {
	id := c.Params("id")

	integrationStore.Lock()
	defer integrationStore.Unlock()

	var found *models.Integration
	for i := range integrationStore.data {
		if integrationStore.data[i].ID == id {
			found = &integrationStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Integration not found",
		})
	}

	found.Config = nil
	found.Status = "not_configured"
	found.LastSync = nil
	found.LastError = ""

	return c.JSON(fiber.Map{
		"message": "Integration " + found.Name + " disconnected successfully",
	})
}
