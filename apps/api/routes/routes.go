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

	// Initialize PostgreSQL store if configured.
	if dsn := os.Getenv("POSTGRES_URL"); dsn != "" {
		pgStore, err := store.NewPostgresStore(dsn, logger)
		if err != nil {
			logger.Warn("Failed to connect to PostgreSQL, using in-memory stores",
				zap.Error(err),
			)
		} else {
			logger.Info("Connected to PostgreSQL")
			_ = pgStore // Available for config store, targets store, etc.
		}
	} else {
		logger.Info("POSTGRES_URL not set, using in-memory stores")
	}

	// Determine auth middleware based on OIDC configuration.
	oidcIssuer := os.Getenv("OIDC_ISSUER_URL")
	oidcClientID := os.Getenv("OIDC_CLIENT_ID")
	authMiddleware := middleware.OIDCAuth(oidcIssuer, oidcClientID)
	if oidcIssuer != "" {
		logger.Info("OIDC authentication configured",
			zap.String("issuer", oidcIssuer),
			zap.String("client_id", oidcClientID),
		)
	} else {
		logger.Info("OIDC not configured, using dev-mode authentication")
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

	// Setup endpoints (no auth required — setup happens before auth is configured).
	setup := api.Group("/setup")
	setup.Get("/status", handlers.GetSetupStatus)
	setup.Post("/config", handlers.SaveConfig)
	setup.Post("/complete", handlers.CompleteSetup)
	setup.Post("/test-connection", handlers.TestConnection)

	// Cloud accounts (no auth required during setup).
	accounts := api.Group("/accounts")
	accounts.Get("/", handlers.ListAccounts)
	accounts.Post("/", handlers.CreateAccount)
	accounts.Put("/:id", handlers.UpdateAccount)
	accounts.Delete("/:id", handlers.DeleteAccount)
	accounts.Post("/:id/test", handlers.TestAccountConnection)

	// Integrations (no auth required during setup).
	integ := api.Group("/integrations")
	integ.Get("/", handlers.ListIntegrations)
	integ.Put("/:id", handlers.UpdateIntegration)
	integ.Post("/:id/test", handlers.TestIntegrationConnection)
	integ.Delete("/:id", handlers.DisconnectIntegration)

	// Authenticated routes.
	authenticated := api.Group("", authMiddleware)

	// Incidents.
	incidents := authenticated.Group("/incidents")
	incidents.Get("/stats", handlers.GetIncidentStats)
	incidents.Get("/", handlers.ListIncidents)
	incidents.Get("/:id", handlers.GetIncident)
	incidents.Post("/", handlers.CreateIncident)
	incidents.Put("/:id", handlers.UpdateIncident)
	incidents.Post("/:id/timeline", handlers.AddTimelineEvent)
	incidents.Post("/:id/acknowledge", handlers.AcknowledgeIncident)
	incidents.Post("/:id/resolve", handlers.ResolveIncident)

	// Alerts.
	alerts := authenticated.Group("/alerts")
	alerts.Get("/", handlers.ListAlerts)
	alerts.Get("/feed", handlers.GetAlertFeed)

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
	slo.Get("/summary", handlers.GetSLOSummary)
	slo.Get("/", handlers.ListSLOs)
	slo.Post("/", handlers.CreateSLO)
	slo.Get("/:id", handlers.GetSLO)
	slo.Put("/:id", handlers.UpdateSLO)
	slo.Delete("/:id", handlers.DeleteSLO)
	slo.Get("/:id/budget", handlers.GetSLOErrorBudget)

	// Services.
	services := authenticated.Group("/services")
	services.Get("/", handlers.ListServices)
	services.Get("/:id", handlers.GetService)
	services.Get("/:id/slos", handlers.GetServiceSLOs)

	// FinOps (Cloud Cost Management).
	finops := authenticated.Group("/finops")
	finops.Get("/summary", handlers.GetFinOpsSummary)
	finops.Get("/costs", handlers.GetFinOpsCosts)
	finops.Get("/trends", handlers.GetFinOpsTrends)
	finops.Get("/anomalies", handlers.GetFinOpsAnomalies)
	finops.Get("/budgets", handlers.GetFinOpsBudgets)
	finops.Get("/kubernetes", handlers.GetFinOpsKubernetes)
	// CSV / XLSX export endpoints (P2.3).
	finops.Get("/export/costs", handlers.ExportFinOpsCosts)
	finops.Get("/export/budgets", handlers.ExportFinOpsBudgets)
	finops.Get("/export/anomalies", handlers.ExportFinOpsAnomalies)
	finops.Get("/export/k8s", handlers.ExportFinOpsKubernetes)

	// Targets (team SLO/MTTR/SLA/ErrorBudget/CostBudget targets).
	targets := authenticated.Group("/targets")
	targets.Get("/", handlers.ListTargets)
	targets.Get("/:account_id", handlers.GetTargets)
	targets.Put("/:account_id", handlers.UpdateTargets)

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
