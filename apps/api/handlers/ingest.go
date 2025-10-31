package handlers

import (
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/junegu/aegis/api/models"
	"github.com/junegu/aegis/api/store"
)

// IngestHandlers holds dependencies for log ingestion endpoints.
type IngestHandlers struct {
	Store  store.Store
	Logger *zap.Logger
}

// NewIngestHandlers creates a new IngestHandlers instance.
func NewIngestHandlers(s store.Store, logger *zap.Logger) *IngestHandlers {
	return &IngestHandlers{
		Store:  s,
		Logger: logger,
	}
}

// IngestLogs accepts a batch of log entries via JSON POST.
// POST /api/v1/ingest/logs
func (h *IngestHandlers) IngestLogs(c *fiber.Ctx) error {
	var req models.IngestLogsRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_payload",
			"message": "Failed to parse request body: " + err.Error(),
		})
	}

	if len(req.Logs) == 0 {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "empty_payload",
			"message": "No log entries provided",
		})
	}

	// Validate entries.
	validEntries := make([]models.LogEntry, 0, len(req.Logs))
	for _, entry := range req.Logs {
		if entry.Message == "" {
			continue
		}
		if entry.Service == "" {
			entry.Service = "unknown"
		}
		if entry.Level == "" {
			entry.Level = "info"
		}
		if entry.Timestamp.IsZero() {
			continue
		}
		validEntries = append(validEntries, entry)
	}

	if len(validEntries) == 0 {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "no_valid_entries",
			"message": "No valid log entries found in payload",
		})
	}

	h.Logger.Info("Ingesting log batch",
		zap.Int("total", len(req.Logs)),
		zap.Int("valid", len(validEntries)),
	)

	// If a store is connected, persist the logs.
	if h.Store != nil {
		if err := h.Store.InsertLogs(c.Context(), validEntries); err != nil {
			h.Logger.Error("Failed to insert logs into store", zap.Error(err))
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "storage_error",
				"message": "Failed to persist log entries",
			})
		}
	}

	return c.Status(fiber.StatusAccepted).JSON(models.IngestResponse{
		Status:   "accepted",
		Accepted: len(validEntries),
		Message:  "Log entries accepted for processing",
	})
}

// IngestOTLP is a placeholder for OpenTelemetry log ingestion.
// POST /api/v1/ingest/otlp
func (h *IngestHandlers) IngestOTLP(c *fiber.Ctx) error {
	body := c.Body()

	h.Logger.Info("Received OTLP log payload",
		zap.Int("payload_size", len(body)),
		zap.String("content_type", c.Get("Content-Type")),
	)

	// TODO: Parse OTLP protobuf or JSON payload and convert to LogEntry format.
	// For now, acknowledge receipt.
	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"status":  "accepted",
		"message": "OTLP log ingestion endpoint — full parsing not yet implemented",
	})
}
