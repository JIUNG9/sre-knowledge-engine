package routes

import (
	"os"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/junegu/aegis/api/handlers"
	"github.com/junegu/aegis/api/middleware"
	"github.com/junegu/aegis/api/store"
)

// Setup registers all API routes on the Fiber app.
func Setup(app *fiber.App, logger *zap.Logger) {
	// Rate limiter: 100 requests per minute per IP.
	rateLimiter := middleware.NewRateLimiter(100, 1*time.Minute)

	// Initialize store (ClickHouse) if configured.
	var logStore store.Store
	if dsn := os.Getenv("CLICKHOUSE_URL"); dsn != "" {
		chStore, err := store.NewClickHouseStore(dsn)
		if err != nil {
			logger.Warn("Failed to connect to ClickHouse, falling back to mock data",
				zap.Error(err),
			)
		} else {
			logStore = chStore
			logger.Info("Connected to ClickHouse")
		}
	} else {
		logger.Info("CLICKHOUSE_URL not set, using mock data for logs")
	}

	// Initialize handlers.
	logHandlers := handlers.NewLogHandlers(logStore, logger)
	ingestHandlers := handlers.NewIngestHandlers(logStore, logger)
	wsHub := handlers.NewWSHub(logger)

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

	// Logs — query endpoints.
	logs := authenticated.Group("/logs")
	logs.Get("/", logHandlers.QueryLogs)
	logs.Get("/stats", logHandlers.GetLogStats)
	logs.Get("/services", logHandlers.GetServices)
	logs.Get("/saved-queries", logHandlers.ListSavedQueries)
	logs.Post("/saved-queries", logHandlers.CreateSavedQuery)

	// Logs — WebSocket streaming (upgrade middleware + handler).
	logs.Use("/stream", handlers.UpgradeMiddleware())
	logs.Get("/stream", websocket.New(wsHub.HandleStreamLogs))

	// SLOs.
	slo := authenticated.Group("/slo")
	slo.Get("/", handlers.ListSLOs)
	slo.Get("/summary", handlers.GetSLOSummary)
	slo.Get("/:id", handlers.GetSLO)

	// Ingestion endpoints (separate from authenticated routes for external sources).
	ingest := api.Group("/ingest")
	ingest.Post("/logs", ingestHandlers.IngestLogs)
	ingest.Post("/otlp", ingestHandlers.IngestOTLP)

	// Webhooks (authenticated with separate webhook tokens in production).
	webhookHandlers := handlers.NewWebhookHandlers(logger)
	webhooks := api.Group("/webhooks")
	webhooks.Post("/signoz", webhookHandlers.HandleSigNoz)
	webhooks.Post("/datadog", webhookHandlers.HandleDatadog)
	webhooks.Post("/prometheus", webhookHandlers.HandlePrometheus)
}
