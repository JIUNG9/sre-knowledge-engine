package handlers

import (
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"

	"github.com/junegu/aegis/api/mock"
	"github.com/junegu/aegis/api/models"
)

// sloStore holds the in-memory SLO data (loaded once from mock generator).
var sloStore []models.SLO

func init() {
	sloStore = mock.GenerateMockSLOs()
}

// ListSLOs returns all SLOs, optionally filtered by service_id, window, sli_type, or status.
//
//	GET /api/v1/slo?service_id=...&window=...&sli_type=...&status=...
func ListSLOs(c *fiber.Ctx) error {
	serviceID := c.Query("service_id")
	window := c.Query("window")
	sliType := c.Query("sli_type")
	status := c.Query("status")

	filtered := make([]models.SLO, 0, len(sloStore))
	for _, slo := range sloStore {
		if serviceID != "" && slo.ServiceID != serviceID {
			continue
		}
		if window != "" && slo.Window != window {
			continue
		}
		if sliType != "" && string(slo.SLIType) != sliType {
			continue
		}
		if status != "" && string(slo.Status) != status {
			continue
		}
		filtered = append(filtered, slo)
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// GetSLO returns a single SLO by ID with current metrics.
//
//	GET /api/v1/slo/:id
func GetSLO(c *fiber.Ctx) error {
	id := c.Params("id")
	for _, slo := range sloStore {
		if slo.ID == id {
			return c.JSON(slo)
		}
	}
	return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
		"error":   "not_found",
		"message": "SLO not found",
	})
}

// CreateSLO creates a new SLO from the request body.
//
//	POST /api/v1/slo
func CreateSLO(c *fiber.Ctx) error {
	var req models.SLOCreateRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	// Validate required fields.
	if req.ServiceID == "" || req.Name == "" || req.Target == 0 || req.Window == "" || req.SLIType == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "service_id, name, target, window, and sli_type are required",
		})
	}

	now := time.Now().UTC()
	budgetTotal := 100.0 - req.Target

	slo := models.SLO{
		ID:                     fmt.Sprintf("slo-%03d", len(sloStore)+1),
		ServiceID:              req.ServiceID,
		Name:                   req.Name,
		Description:            req.Description,
		Target:                 req.Target,
		Current:                req.Target, // Starts at target (no data yet).
		Window:                 req.Window,
		SLIType:                req.SLIType,
		ErrorBudgetTotal:       budgetTotal,
		ErrorBudgetRemaining:   100.0, // Full budget at creation.
		ErrorBudgetConsumedPct: 0.0,
		BurnRate:               0.0,
		Status:                 models.SLOStatusMeeting,
		CreatedAt:              now,
		UpdatedAt:              now,
	}

	sloStore = append(sloStore, slo)

	return c.Status(fiber.StatusCreated).JSON(slo)
}

// UpdateSLO updates an existing SLO with partial updates.
//
//	PUT /api/v1/slo/:id
func UpdateSLO(c *fiber.Ctx) error {
	id := c.Params("id")

	var found *models.SLO
	for i := range sloStore {
		if sloStore[i].ID == id {
			found = &sloStore[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "SLO not found",
		})
	}

	var req models.SLOUpdateRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	if req.Name != nil {
		found.Name = *req.Name
	}
	if req.Description != nil {
		found.Description = *req.Description
	}
	if req.Target != nil {
		found.Target = *req.Target
		found.ErrorBudgetTotal = 100.0 - *req.Target
	}
	if req.Window != nil {
		found.Window = *req.Window
	}
	if req.SLIType != nil {
		found.SLIType = *req.SLIType
	}
	found.UpdatedAt = time.Now().UTC()

	return c.JSON(found)
}

// DeleteSLO removes an SLO by ID.
//
//	DELETE /api/v1/slo/:id
func DeleteSLO(c *fiber.Ctx) error {
	id := c.Params("id")

	for i, slo := range sloStore {
		if slo.ID == id {
			sloStore = append(sloStore[:i], sloStore[i+1:]...)
			return c.Status(fiber.StatusNoContent).Send(nil)
		}
	}

	return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
		"error":   "not_found",
		"message": "SLO not found",
	})
}

// GetSLOErrorBudget returns the error budget time series for a specific SLO.
//
//	GET /api/v1/slo/:id/budget
func GetSLOErrorBudget(c *fiber.Ctx) error {
	id := c.Params("id")

	// Verify the SLO exists.
	var found *models.SLO
	for i := range sloStore {
		if sloStore[i].ID == id {
			found = &sloStore[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "SLO not found",
		})
	}

	// Determine the number of days based on the SLO window.
	days := 30
	switch found.Window {
	case "7d":
		days = 7
	case "30d":
		days = 30
	case "90d":
		days = 90
	case "365d":
		days = 365
	}

	// Cap at 30 data points for charting (aggregate if window > 30d).
	dataPointCount := days
	if dataPointCount > 30 {
		dataPointCount = 30
	}

	dataPoints := mock.GenerateMockErrorBudget(id, dataPointCount)

	timeSeries := models.SLOTimeSeries{
		SLOID:      id,
		DataPoints: dataPoints,
	}

	return c.JSON(timeSeries)
}

// GetSLOSummary returns an aggregate summary of all SLOs.
//
//	GET /api/v1/slo/summary
func GetSLOSummary(c *fiber.Ctx) error {
	meeting := 0
	atRisk := 0
	breaching := 0
	totalBudget := 0.0

	for _, slo := range sloStore {
		switch slo.Status {
		case models.SLOStatusMeeting:
			meeting++
		case models.SLOStatusAtRisk:
			atRisk++
		case models.SLOStatusBreaching:
			breaching++
		}
		totalBudget += slo.ErrorBudgetRemaining
	}

	avg := 0.0
	if len(sloStore) > 0 {
		avg = totalBudget / float64(len(sloStore))
	}

	summary := models.SLOSummary{
		TotalSLOs:          len(sloStore),
		Meeting:            meeting,
		AtRisk:             atRisk,
		Breaching:          breaching,
		AverageErrorBudget: avg,
	}

	return c.JSON(summary)
}

// GetServiceSLOs returns all SLOs for a specific service.
// This is called from the services handler but lives here since it operates on SLO data.
func GetServiceSLOs(c *fiber.Ctx) error {
	serviceID := c.Params("id")

	filtered := make([]models.SLO, 0)
	for _, slo := range sloStore {
		if slo.ServiceID == serviceID {
			filtered = append(filtered, slo)
		}
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}
