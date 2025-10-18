package handlers

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/junegu/aegis/api/models"
)

// Mock incident data for development.
var mockIncidents = []models.Incident{
	{
		ID:          "INC-001",
		Title:       "Payment service high error rate",
		Severity:    models.SeverityCritical,
		Status:      models.IncidentStatusInvestigating,
		Service:     "payment-service",
		Assignee:    "oncall-sre",
		Description: "Payment service returning 500 errors at 15% rate, affecting checkout flow.",
		CreatedAt:   time.Date(2026, 4, 10, 8, 30, 0, 0, time.UTC),
		UpdatedAt:   time.Date(2026, 4, 10, 9, 15, 0, 0, time.UTC),
	},
	{
		ID:          "INC-002",
		Title:       "Elevated latency on user-service /api/v1/profile",
		Severity:    models.SeverityHigh,
		Status:      models.IncidentStatusOpen,
		Service:     "user-service",
		Assignee:    "",
		Description: "P99 latency increased from 200ms to 1.2s on profile endpoint.",
		CreatedAt:   time.Date(2026, 4, 10, 10, 0, 0, 0, time.UTC),
		UpdatedAt:   time.Date(2026, 4, 10, 10, 0, 0, 0, time.UTC),
	},
	{
		ID:          "INC-003",
		Title:       "Kubernetes node NotReady in prod-us-east-1",
		Severity:    models.SeverityMedium,
		Status:      models.IncidentStatusResolved,
		Service:     "infrastructure",
		Assignee:    "platform-team",
		Description: "Node i-0abc123 entered NotReady state due to kubelet OOM.",
		RootCause:   "Memory leak in logging sidecar container consuming 4Gi. Fixed by updating sidecar image to v2.3.1.",
		CreatedAt:   time.Date(2026, 4, 9, 14, 0, 0, 0, time.UTC),
		UpdatedAt:   time.Date(2026, 4, 9, 16, 45, 0, 0, time.UTC),
	},
	{
		ID:          "INC-004",
		Title:       "Certificate expiry warning for api.aegis.dev",
		Severity:    models.SeverityLow,
		Status:      models.IncidentStatusOpen,
		Service:     "gateway",
		Assignee:    "infra-oncall",
		Description: "TLS certificate for api.aegis.dev expires in 7 days. Auto-renewal may have failed.",
		CreatedAt:   time.Date(2026, 4, 10, 6, 0, 0, 0, time.UTC),
		UpdatedAt:   time.Date(2026, 4, 10, 6, 0, 0, 0, time.UTC),
	},
}

// ListIncidents returns all incidents.
func ListIncidents(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"data":  mockIncidents,
		"total": len(mockIncidents),
	})
}

// GetIncident returns a single incident by ID.
func GetIncident(c *fiber.Ctx) error {
	id := c.Params("id")
	for _, inc := range mockIncidents {
		if inc.ID == id {
			return c.JSON(inc)
		}
	}
	return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
		"error":   "not_found",
		"message": "Incident not found",
	})
}

// CreateIncident creates a new incident.
func CreateIncident(c *fiber.Ctx) error {
	var req models.CreateIncidentRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	now := time.Now().UTC()
	incident := models.Incident{
		ID:          "INC-005",
		Title:       req.Title,
		Severity:    req.Severity,
		Status:      models.IncidentStatusOpen,
		Service:     req.Service,
		Assignee:    req.Assignee,
		Description: req.Description,
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	return c.Status(fiber.StatusCreated).JSON(incident)
}

// UpdateIncident updates an existing incident.
func UpdateIncident(c *fiber.Ctx) error {
	id := c.Params("id")

	var found *models.Incident
	for i := range mockIncidents {
		if mockIncidents[i].ID == id {
			found = &mockIncidents[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Incident not found",
		})
	}

	var req models.UpdateIncidentRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	// Apply partial updates.
	if req.Title != nil {
		found.Title = *req.Title
	}
	if req.Severity != nil {
		found.Severity = *req.Severity
	}
	if req.Status != nil {
		found.Status = *req.Status
	}
	if req.Assignee != nil {
		found.Assignee = *req.Assignee
	}
	if req.Description != nil {
		found.Description = *req.Description
	}
	if req.RootCause != nil {
		found.RootCause = *req.RootCause
	}
	found.UpdatedAt = time.Now().UTC()

	return c.JSON(found)
}
