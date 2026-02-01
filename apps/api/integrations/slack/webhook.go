package slack

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// InteractionPayload represents a Slack interactive message callback.
type InteractionPayload struct {
	Type    string `json:"type"`
	User    struct {
		ID       string `json:"id"`
		Username string `json:"username"`
		Name     string `json:"name"`
	} `json:"user"`
	Actions []struct {
		ActionID string `json:"action_id"`
		Value    string `json:"value"`
		Type     string `json:"type"`
	} `json:"actions"`
	Channel struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	} `json:"channel"`
	ResponseURL string `json:"response_url"`
}

// WebhookHandler handles incoming Slack interaction callbacks.
type WebhookHandler struct {
	client    *Client
	logger    *zap.Logger
	approvals map[string]*ApprovalResponse // in-memory approval store
}

// NewWebhookHandler creates a new Slack webhook handler.
func NewWebhookHandler(client *Client, logger *zap.Logger) *WebhookHandler {
	return &WebhookHandler{
		client:    client,
		logger:    logger,
		approvals: make(map[string]*ApprovalResponse),
	}
}

// HandleInteraction processes Slack interactive message callbacks.
func (h *WebhookHandler) HandleInteraction(c *fiber.Ctx) error {
	var payload InteractionPayload
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "invalid payload"})
	}

	for _, action := range payload.Actions {
		h.logger.Info("Slack interaction received",
			zap.String("action", action.ActionID),
			zap.String("user", payload.User.Username),
			zap.String("value", action.Value),
		)

		response := &ApprovalResponse{
			User:      payload.User.Username,
			Timestamp: time.Now().UTC().Format(time.RFC3339),
		}

		switch {
		case len(action.ActionID) > 13 && action.ActionID[:13] == "approve_step_":
			response.Action = "approve"
			response.StepID = action.ActionID[13:]
			h.approvals[action.Value] = response
			h.logger.Info("Remediation step approved",
				zap.String("step", response.StepID),
				zap.String("approved_by", response.User))

		case len(action.ActionID) > 12 && action.ActionID[:12] == "reject_step_":
			response.Action = "reject"
			response.StepID = action.ActionID[12:]
			h.approvals[action.Value] = response
			h.logger.Info("Remediation step rejected",
				zap.String("step", response.StepID),
				zap.String("rejected_by", response.User))

		case action.ActionID == "investigate_incident":
			h.logger.Info("AI investigation triggered from Slack",
				zap.String("incident_id", action.Value))

		case action.ActionID == "acknowledge_incident":
			h.logger.Info("Incident acknowledged from Slack",
				zap.String("incident_id", action.Value))
		}
	}

	return c.SendStatus(200)
}

// GetApproval checks if a remediation step has been approved or rejected.
func (h *WebhookHandler) GetApproval(incidentID, stepID string) *ApprovalResponse {
	key := fmt.Sprintf("%s:%s", incidentID, stepID)
	return h.approvals[key]
}

// VerifySignature validates the Slack request signature.
func (h *WebhookHandler) VerifySignature(c *fiber.Ctx) bool {
	if h.client.signingSecret == "" {
		return true // skip in dev
	}

	timestamp := c.Get("X-Slack-Request-Timestamp")
	signature := c.Get("X-Slack-Signature")

	baseString := fmt.Sprintf("v0:%s:%s", timestamp, string(c.Body()))
	mac := hmac.New(sha256.New, []byte(h.client.signingSecret))
	mac.Write([]byte(baseString))
	expected := "v0=" + hex.EncodeToString(mac.Sum(nil))

	return hmac.Equal([]byte(expected), []byte(signature))
}
