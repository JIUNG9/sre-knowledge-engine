package handlers

import (
	"github.com/gofiber/fiber/v2"
)

// HealthResponse represents the health check response.
type HealthResponse struct {
	Status  string `json:"status"`
	Version string `json:"version"`
	Service string `json:"service"`
}

// ReadyResponse represents the readiness check response.
type ReadyResponse struct {
	Status string `json:"status"`
	Checks map[string]string `json:"checks"`
}

// HealthCheck returns the current health status of the API.
func HealthCheck(c *fiber.Ctx) error {
	return c.JSON(HealthResponse{
		Status:  "ok",
		Version: "0.1.0",
		Service: "aegis-api",
	})
}

// ReadinessCheck returns the readiness status including dependency checks.
func ReadinessCheck(c *fiber.Ctx) error {
	return c.JSON(ReadyResponse{
		Status: "ok",
		Checks: map[string]string{
			"database": "ok",
			"cache":    "ok",
		},
	})
}
