package handlers

import (
	"github.com/gofiber/fiber/v2"

	"github.com/junegu/aegis/api/mock"
	"github.com/junegu/aegis/api/models"
)

// serviceStore holds the in-memory service catalog (loaded once from mock generator).
var serviceStore []models.Service

func init() {
	serviceStore = mock.GenerateMockServices()
}

// ListServices returns all services with health status.
//
//	GET /api/v1/services?status=...&team=...&tier=...
func ListServices(c *fiber.Ctx) error {
	status := c.Query("status")
	team := c.Query("team")
	tier := c.Query("tier")

	filtered := make([]models.Service, 0, len(serviceStore))
	for _, svc := range serviceStore {
		if status != "" && string(svc.Status) != status {
			continue
		}
		if team != "" && svc.Team != team {
			continue
		}
		if tier != "" && svc.Tier != tier {
			continue
		}
		filtered = append(filtered, svc)
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// GetService returns a single service by ID with full metadata.
//
//	GET /api/v1/services/:id
func GetService(c *fiber.Ctx) error {
	id := c.Params("id")
	for _, svc := range serviceStore {
		if svc.ID == id {
			return c.JSON(svc)
		}
	}
	return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
		"error":   "not_found",
		"message": "Service not found",
	})
}
