package routes

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/junegu/aegis/api/handlers"
	"github.com/junegu/aegis/api/middleware"
	"go.uber.org/zap"
)

// Setup registers all API routes on the Fiber app.
func Setup(app *fiber.App, logger *zap.Logger) {
	// Rate limiter: 100 requests per minute per IP.
	rateLimiter := middleware.NewRateLimiter(100, 1*time.Minute)

	// API v1 group.
	api := app.Group("/api/v1", rateLimiter.Handler())

	// Health endpoints (no auth required).
	api.Get("/health", handlers.HealthCheck)
	api.Get("/ready", handlers.ReadinessCheck)

	// Authenticated routes.
	authenticated := api.Group("", middleware.Auth())

	// Incidents.
	incidents := authenticated.Group("/incidents")
	incidents.Get("/", handlers.ListIncidents)
	incidents.Get("/:id", handlers.GetIncident)
	incidents.Post("/", handlers.CreateIncident)
	incidents.Put("/:id", handlers.UpdateIncident)

	// Logs.
	logs := authenticated.Group("/logs")
	logs.Get("/", handlers.QueryLogs)
	logs.Get("/stream", handlers.StreamLogs)

	// SLOs.
	slo := authenticated.Group("/slo")
	slo.Get("/", handlers.ListSLOs)
	slo.Get("/summary", handlers.GetSLOSummary)
	slo.Get("/:id", handlers.GetSLO)

	// Webhooks (authenticated with separate webhook tokens in production).
	webhookHandlers := handlers.NewWebhookHandlers(logger)
	webhooks := api.Group("/webhooks")
	webhooks.Post("/signoz", webhookHandlers.HandleSigNoz)
	webhooks.Post("/datadog", webhookHandlers.HandleDatadog)
	webhooks.Post("/prometheus", webhookHandlers.HandlePrometheus)
}
