package handlers

import (
	"github.com/gofiber/fiber/v2"
	"github.com/junegu/aegis/api/models"
)

// Mock SLO data for development.
var mockSLOs = []models.SLO{
	{
		ID:                   "slo-001",
		ServiceID:            "payment-service",
		Name:                 "Payment API Availability",
		Target:               99.95,
		Current:              99.87,
		Window:               "30d",
		SLIType:              models.SLITypeAvailability,
		ErrorBudgetRemaining: 23.4,
	},
	{
		ID:                   "slo-002",
		ServiceID:            "payment-service",
		Name:                 "Payment API Latency P99",
		Target:               99.0,
		Current:              98.5,
		Window:               "30d",
		SLIType:              models.SLITypeLatency,
		ErrorBudgetRemaining: 50.0,
	},
	{
		ID:                   "slo-003",
		ServiceID:            "user-service",
		Name:                 "User Service Availability",
		Target:               99.9,
		Current:              99.95,
		Window:               "30d",
		SLIType:              models.SLITypeAvailability,
		ErrorBudgetRemaining: 75.0,
	},
	{
		ID:                   "slo-004",
		ServiceID:            "gateway",
		Name:                 "Gateway Error Rate",
		Target:               99.99,
		Current:              99.98,
		Window:               "7d",
		SLIType:              models.SLITypeErrorRate,
		ErrorBudgetRemaining: 80.0,
	},
}

// ListSLOs returns all SLOs, optionally filtered by service.
func ListSLOs(c *fiber.Ctx) error {
	serviceID := c.Query("service_id")

	if serviceID == "" {
		return c.JSON(fiber.Map{
			"data":  mockSLOs,
			"total": len(mockSLOs),
		})
	}

	filtered := make([]models.SLO, 0)
	for _, slo := range mockSLOs {
		if slo.ServiceID == serviceID {
			filtered = append(filtered, slo)
		}
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// GetSLO returns a single SLO by ID.
func GetSLO(c *fiber.Ctx) error {
	id := c.Params("id")
	for _, slo := range mockSLOs {
		if slo.ID == id {
			return c.JSON(slo)
		}
	}
	return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
		"error":   "not_found",
		"message": "SLO not found",
	})
}

// SLOSummary returns a high-level overview of SLO compliance.
type SLOSummaryResponse struct {
	Total     int     `json:"total"`
	Meeting   int     `json:"meeting"`
	Breaching int     `json:"breaching"`
	Average   float64 `json:"average_budget_remaining"`
}

// GetSLOSummary returns an aggregate summary of all SLOs.
func GetSLOSummary(c *fiber.Ctx) error {
	meeting := 0
	breaching := 0
	totalBudget := 0.0

	for _, slo := range mockSLOs {
		if slo.Current >= slo.Target {
			meeting++
		} else {
			breaching++
		}
		totalBudget += slo.ErrorBudgetRemaining
	}

	avg := 0.0
	if len(mockSLOs) > 0 {
		avg = totalBudget / float64(len(mockSLOs))
	}

	return c.JSON(SLOSummaryResponse{
		Total:     len(mockSLOs),
		Meeting:   meeting,
		Breaching: breaching,
		Average:   avg,
	})
}
