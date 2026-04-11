package slack

import (
	"fmt"
	"net/http"
	"time"

	"github.com/junegu/aegis/api/integrations"
)

// Adapter implements integrations.Adapter for Slack.
// It wraps the existing Client to provide the unified adapter interface.
type Adapter struct {
	botToken      string
	signingSecret string
	channel       string
	httpClient    *http.Client
	connected     bool
}

// NewAdapter creates a new Slack adapter.
func NewAdapter() *Adapter {
	return &Adapter{
		httpClient: &http.Client{Timeout: 10 * time.Second},
	}
}

// ID returns the unique identifier for the Slack adapter.
func (a *Adapter) ID() string { return "slack" }

// Name returns the human-readable name.
func (a *Adapter) Name() string { return "Slack" }

// Category returns the adapter category.
func (a *Adapter) Category() string { return "notification" }

// Connect validates and stores the Slack connection configuration.
func (a *Adapter) Connect(config map[string]string) error {
	token, ok := config["bot_token"]
	if !ok || token == "" {
		return fmt.Errorf("Slack bot token is required")
	}

	secret := config["signing_secret"]
	channel := config["channel"]
	if channel == "" {
		channel = "#aegis-alerts"
	}

	a.botToken = token
	a.signingSecret = secret
	a.channel = channel
	a.connected = true
	return nil
}

// Test verifies the Slack connection by calling the auth.test API.
func (a *Adapter) Test() (*integrations.HealthResult, error) {
	if !a.connected {
		return &integrations.HealthResult{
			Healthy: false,
			Message: "Not connected. Call Connect() first.",
		}, nil
	}

	start := time.Now()

	req, err := http.NewRequest("POST", "https://slack.com/api/auth.test", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+a.botToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := a.httpClient.Do(req)
	latency := int(time.Since(start).Milliseconds())

	if err != nil {
		return &integrations.HealthResult{
			Healthy: false,
			Message: fmt.Sprintf("Connection failed: %v", err),
			Latency: latency,
		}, nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return &integrations.HealthResult{
			Healthy: false,
			Message: fmt.Sprintf("Slack returned HTTP %d", resp.StatusCode),
			Latency: latency,
		}, nil
	}

	return &integrations.HealthResult{
		Healthy: true,
		Message: "Slack connection is healthy",
		Latency: latency,
	}, nil
}

// Sync is a no-op for Slack since it is a push-based integration.
// Returns success with 0 items synced.
func (a *Adapter) Sync() (*integrations.SyncResult, error) {
	if !a.connected {
		return nil, fmt.Errorf("not connected")
	}

	return &integrations.SyncResult{
		Success:  true,
		Items:    0,
		Duration: 0,
		Message:  "Slack is push-based; no data to sync",
	}, nil
}

// Disconnect clears the Slack connection configuration.
func (a *Adapter) Disconnect() error {
	a.botToken = ""
	a.signingSecret = ""
	a.channel = ""
	a.connected = false
	return nil
}

// ConfigSchema returns the configuration fields required by Slack.
func (a *Adapter) ConfigSchema() []integrations.ConfigField {
	return []integrations.ConfigField{
		{
			Key:         "bot_token",
			Label:       "Bot Token",
			Type:        "password",
			Required:    true,
			Placeholder: "xoxb-...",
			HelpText:    "Slack Bot User OAuth Token. Found in your Slack App settings under OAuth & Permissions.",
		},
		{
			Key:         "signing_secret",
			Label:       "Signing Secret",
			Type:        "password",
			Required:    false,
			Placeholder: "Enter signing secret",
			HelpText:    "Used to verify incoming webhook requests from Slack. Found in Basic Information.",
		},
		{
			Key:         "channel",
			Label:       "Default Channel",
			Type:        "text",
			Required:    false,
			Placeholder: "#aegis-alerts",
			HelpText:    "Default channel for incident notifications. Defaults to #aegis-alerts.",
		},
	}
}

// Compile-time interface check.
var _ integrations.Adapter = (*Adapter)(nil)
