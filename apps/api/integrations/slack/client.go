// Package slack provides Slack integration for incident notifications
// and auto-remediation approval workflows.
package slack

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"go.uber.org/zap"
)

// Client handles communication with the Slack API.
type Client struct {
	botToken      string
	signingSecret string
	httpClient    *http.Client
	logger        *zap.Logger
}

// NewClient creates a new Slack client.
func NewClient(logger *zap.Logger) *Client {
	return &Client{
		botToken:      os.Getenv("SLACK_BOT_TOKEN"),
		signingSecret: os.Getenv("SLACK_SIGNING_SECRET"),
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		logger: logger,
	}
}

// IsConfigured returns true if Slack credentials are set.
func (c *Client) IsConfigured() bool {
	return c.botToken != "" && c.signingSecret != ""
}

// IncidentNotification represents an incident notification payload.
type IncidentNotification struct {
	IncidentID  string `json:"incident_id"`
	Title       string `json:"title"`
	Severity    string `json:"severity"`
	Service     string `json:"service"`
	Summary     string `json:"summary"`
	RootCause   string `json:"root_cause,omitempty"`
	Channel     string `json:"channel"`
}

// RemediationApproval represents a remediation approval request.
type RemediationApproval struct {
	IncidentID    string            `json:"incident_id"`
	Title         string            `json:"title"`
	Steps         []RemediationStep `json:"steps"`
	Channel       string            `json:"channel"`
	RequestedBy   string            `json:"requested_by"`
}

// RemediationStep is a single remediation action requiring approval.
type RemediationStep struct {
	ID          string `json:"id"`
	Description string `json:"description"`
	Command     string `json:"command"`
	RiskLevel   string `json:"risk_level"` // low, medium, high
}

// ApprovalResponse represents a user's response to an approval request.
type ApprovalResponse struct {
	IncidentID string `json:"incident_id"`
	StepID     string `json:"step_id"`
	Action     string `json:"action"` // approve, reject
	User       string `json:"user"`
	Timestamp  string `json:"timestamp"`
}

// Block represents a Slack Block Kit element.
type Block map[string]interface{}

// SendIncidentNotification posts an incident alert to a Slack channel.
func (c *Client) SendIncidentNotification(notif IncidentNotification) error {
	if !c.IsConfigured() {
		c.logger.Warn("Slack not configured, skipping notification",
			zap.String("incident_id", notif.IncidentID))
		return nil
	}

	severityEmoji := map[string]string{
		"critical": "🔴",
		"high":     "🟠",
		"medium":   "🟡",
		"low":      "🔵",
	}

	blocks := []Block{
		{
			"type": "header",
			"text": Block{
				"type": "plain_text",
				"text": fmt.Sprintf("%s Incident: %s", severityEmoji[notif.Severity], notif.Title),
			},
		},
		{
			"type": "section",
			"fields": []Block{
				{"type": "mrkdwn", "text": fmt.Sprintf("*Severity:* %s", notif.Severity)},
				{"type": "mrkdwn", "text": fmt.Sprintf("*Service:* %s", notif.Service)},
				{"type": "mrkdwn", "text": fmt.Sprintf("*ID:* %s", notif.IncidentID)},
			},
		},
		{
			"type": "section",
			"text": Block{
				"type": "mrkdwn",
				"text": fmt.Sprintf("*Summary:*\n%s", notif.Summary),
			},
		},
		{
			"type": "actions",
			"elements": []Block{
				{
					"type":      "button",
					"text":      Block{"type": "plain_text", "text": "🔍 Investigate"},
					"action_id": "investigate_incident",
					"value":     notif.IncidentID,
					"style":     "primary",
				},
				{
					"type":      "button",
					"text":      Block{"type": "plain_text", "text": "👤 Acknowledge"},
					"action_id": "acknowledge_incident",
					"value":     notif.IncidentID,
				},
			},
		},
	}

	return c.postMessage(notif.Channel, blocks)
}

// SendRemediationApproval posts an approval request to a Slack channel.
func (c *Client) SendRemediationApproval(approval RemediationApproval) error {
	if !c.IsConfigured() {
		c.logger.Warn("Slack not configured, skipping approval request",
			zap.String("incident_id", approval.IncidentID))
		return nil
	}

	blocks := []Block{
		{
			"type": "header",
			"text": Block{
				"type": "plain_text",
				"text": fmt.Sprintf("🤖 AI Remediation Proposal — %s", approval.Title),
			},
		},
		{"type": "divider"},
	}

	for _, step := range approval.Steps {
		riskEmoji := map[string]string{"low": "🟢", "medium": "🟡", "high": "🔴"}

		blocks = append(blocks, Block{
			"type": "section",
			"text": Block{
				"type": "mrkdwn",
				"text": fmt.Sprintf("%s *%s*\n```%s```\nRisk: %s",
					riskEmoji[step.RiskLevel], step.Description, step.Command, step.RiskLevel),
			},
		})

		blocks = append(blocks, Block{
			"type": "actions",
			"elements": []Block{
				{
					"type":      "button",
					"text":      Block{"type": "plain_text", "text": "✅ Approve"},
					"action_id": fmt.Sprintf("approve_step_%s", step.ID),
					"value":     fmt.Sprintf("%s:%s", approval.IncidentID, step.ID),
					"style":     "primary",
				},
				{
					"type":      "button",
					"text":      Block{"type": "plain_text", "text": "❌ Reject"},
					"action_id": fmt.Sprintf("reject_step_%s", step.ID),
					"value":     fmt.Sprintf("%s:%s", approval.IncidentID, step.ID),
					"style":     "danger",
				},
				{
					"type":      "button",
					"text":      Block{"type": "plain_text", "text": "🔍 More Info"},
					"action_id": fmt.Sprintf("info_step_%s", step.ID),
					"value":     fmt.Sprintf("%s:%s", approval.IncidentID, step.ID),
				},
			},
		})
	}

	return c.postMessage(approval.Channel, blocks)
}

// SendResolutionNotification posts a resolution confirmation.
func (c *Client) SendResolutionNotification(channel, incidentID, title, summary string) error {
	if !c.IsConfigured() {
		return nil
	}

	blocks := []Block{
		{
			"type": "header",
			"text": Block{
				"type": "plain_text",
				"text": fmt.Sprintf("✅ Resolved: %s", title),
			},
		},
		{
			"type": "section",
			"text": Block{
				"type": "mrkdwn",
				"text": fmt.Sprintf("*Incident %s resolved.*\n\n%s", incidentID, summary),
			},
		},
	}

	return c.postMessage(channel, blocks)
}

func (c *Client) postMessage(channel string, blocks []Block) error {
	payload := map[string]interface{}{
		"channel": channel,
		"blocks":  blocks,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal slack payload: %w", err)
	}

	req, err := http.NewRequest("POST", "https://slack.com/api/chat.postMessage", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("create slack request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.botToken)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("send slack message: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("slack API returned status %d", resp.StatusCode)
	}

	c.logger.Info("Slack message sent", zap.String("channel", channel))
	return nil
}
