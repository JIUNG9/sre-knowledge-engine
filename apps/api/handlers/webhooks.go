package handlers

import (
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// WebhookHandlers holds dependencies for webhook handlers.
type WebhookHandlers struct {
	Logger *zap.Logger
}

// NewWebhookHandlers creates a new WebhookHandlers instance.
func NewWebhookHandlers(logger *zap.Logger) *WebhookHandlers {
	return &WebhookHandlers{Logger: logger}
}

// HandleSigNoz receives webhooks from SigNoz / Alertmanager.
// SigNoz uses the Alertmanager webhook format.
func (h *WebhookHandlers) HandleSigNoz(c *fiber.Ctx) error {
	body := c.Body()
	h.Logger.Info("Received SigNoz/Alertmanager webhook",
		zap.Int("payload_size", len(body)),
		zap.String("content_type", c.Get("Content-Type")),
	)

	// TODO: Parse Alertmanager payload and create/update incidents.
	return c.JSON(fiber.Map{
		"status":  "received",
		"source":  "signoz",
		"message": "Webhook processed successfully",
	})
}

// HandleDatadog receives webhooks from Datadog.
func (h *WebhookHandlers) HandleDatadog(c *fiber.Ctx) error {
	body := c.Body()
	h.Logger.Info("Received Datadog webhook",
		zap.Int("payload_size", len(body)),
		zap.String("content_type", c.Get("Content-Type")),
	)

	// TODO: Parse Datadog webhook payload and create/update incidents.
	return c.JSON(fiber.Map{
		"status":  "received",
		"source":  "datadog",
		"message": "Webhook processed successfully",
	})
}

// HandlePrometheus receives webhooks from Prometheus Alertmanager.
func (h *WebhookHandlers) HandlePrometheus(c *fiber.Ctx) error {
	body := c.Body()
	h.Logger.Info("Received Prometheus Alertmanager webhook",
		zap.Int("payload_size", len(body)),
		zap.String("content_type", c.Get("Content-Type")),
	)

	// TODO: Parse Prometheus Alertmanager payload and create/update incidents.
	return c.JSON(fiber.Map{
		"status":  "received",
		"source":  "prometheus",
		"message": "Webhook processed successfully",
	})
}
